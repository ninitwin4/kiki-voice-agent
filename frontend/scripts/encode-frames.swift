// encode-frames.swift — turns the screencast frames captured by record-demo.mjs
// into an H.264 MP4 using AVFoundation (built into macOS; no ffmpeg needed).
//
// Screencast frames arrive only when the page changes, so they're variable-rate.
// This resamples them to a constant frame rate on a time map:
//
//   [ hold on landing ] [ demo, sped up by --speed ] [ hold on final state ]
//
// Usage (normally invoked by record-demo.mjs, after `swiftc -O`):
//   encode-frames <manifest.json> <out.mp4> [--speed 1.75] [--hold-start 1]
//                 [--hold-end 2.5] [--width 1440] [--fps 30] [--bitrate 1800000]
//                 [--poster poster.jpg]

import AVFoundation
import CoreGraphics
import Foundation
import ImageIO
import UniformTypeIdentifiers

struct Frame: Decodable { let file: String; let t: Double }
struct Manifest: Decodable {
  let dir: String
  let frames: [Frame]
  let cropFraction: Double  // keep the top fraction of each frame; below it is the demo bar
  let playAt: Double
  let doneAt: Double
}

func die(_ msg: String) -> Never {
  FileHandle.standardError.write(("✗ encode-frames: " + msg + "\n").data(using: .utf8)!)
  exit(1)
}

// --- args ---
let argv = CommandLine.arguments
guard argv.count >= 3 else { die("usage: encode-frames <manifest.json> <out.mp4> [options]") }
var opts: [String: String] = [:]
var i = 3
while i + 1 < argv.count { opts[String(argv[i].dropFirst(2))] = argv[i + 1]; i += 2 }
let speed = Double(opts["speed"] ?? "1") ?? 1
let holdStart = Double(opts["hold-start"] ?? "1") ?? 1
let holdEnd = Double(opts["hold-end"] ?? "2.5") ?? 2.5
let outWidth = Int(opts["width"] ?? "1440") ?? 1440
let fps = Int32(opts["fps"] ?? "30") ?? 30
let bitrate = Int(opts["bitrate"] ?? "1800000") ?? 1_800_000
let posterPath = opts["poster"]

guard let manifestData = FileManager.default.contents(atPath: argv[1]),
  let manifest = try? JSONDecoder().decode(Manifest.self, from: manifestData)
else { die("can't read manifest \(argv[1])") }
let frames = manifest.frames.sorted { $0.t < $1.t }
guard !frames.isEmpty else { die("manifest has no frames") }

// Frame timestamps and playAt/doneAt are both wall-clock seconds. If they somehow
// don't line up, anchor Play to just after the first frame (the recorder waits
// 0.8s before clicking) rather than producing a broken time map.
var playAt = manifest.playAt
var doneAt = manifest.doneAt
if playAt < frames.first!.t - 5 || playAt > frames.last!.t + 5 {
  print("  ! frame clock doesn't match page clock — re-anchoring")
  let length = doneAt - playAt
  playAt = frames.first!.t + 0.8
  doneAt = playAt + length
}

// --- geometry ---
let srgb = CGColorSpace(name: CGColorSpace.sRGB)!
let bitmapInfo = CGImageAlphaInfo.premultipliedFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue

func load(_ f: Frame) -> CGImage {
  let url = URL(fileURLWithPath: manifest.dir).appendingPathComponent(f.file)
  guard let src = CGImageSourceCreateWithURL(url as CFURL, nil),
    let img = CGImageSourceCreateImageAtIndex(src, 0, nil)
  else { die("can't decode \(f.file)") }
  return img
}

let first = load(frames[0])
let cropH = Int((Double(first.height) * manifest.cropFraction).rounded(.down))
guard cropH > 0 && cropH <= first.height else { die("bad crop fraction \(manifest.cropFraction)") }
let scale = Double(outWidth) / Double(first.width)
let outW = outWidth / 2 * 2
let outH = Int((Double(cropH) * scale).rounded()) / 2 * 2  // H.264 wants even dimensions
if scale > 1 {
  print("  ! source frames are \(first.width)px wide — upscaling to \(outW) will look soft")
}

/// Crop off the demo bar and scale to the output size, once per source frame.
func render(_ img: CGImage) -> CGImage {
  guard let cropped = img.cropping(to: CGRect(x: 0, y: 0, width: img.width, height: cropH)),
    let ctx = CGContext(
      data: nil, width: outW, height: outH, bitsPerComponent: 8, bytesPerRow: 0,
      space: srgb, bitmapInfo: bitmapInfo)
  else { die("render failed") }
  ctx.interpolationQuality = .high
  ctx.draw(cropped, in: CGRect(x: 0, y: 0, width: outW, height: outH))
  return ctx.makeImage()!
}

// --- writer ---
let outURL = URL(fileURLWithPath: argv[2])
try? FileManager.default.removeItem(at: outURL)
guard let writer = try? AVAssetWriter(outputURL: outURL, fileType: .mp4) else { die("can't create writer") }
let input = AVAssetWriterInput(
  mediaType: .video,
  outputSettings: [
    AVVideoCodecKey: AVVideoCodecType.h264,
    AVVideoWidthKey: outW,
    AVVideoHeightKey: outH,
    AVVideoColorPropertiesKey: [
      AVVideoColorPrimariesKey: AVVideoColorPrimaries_ITU_R_709_2,
      AVVideoTransferFunctionKey: AVVideoTransferFunction_ITU_R_709_2,
      AVVideoYCbCrMatrixKey: AVVideoYCbCrMatrix_ITU_R_709_2,
    ],
    AVVideoCompressionPropertiesKey: [
      AVVideoAverageBitRateKey: bitrate,
      AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
      AVVideoMaxKeyFrameIntervalKey: Int(fps) * 2,
    ],
  ])
input.expectsMediaDataInRealTime = false
let adaptor = AVAssetWriterInputPixelBufferAdaptor(
  assetWriterInput: input,
  sourcePixelBufferAttributes: [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
    kCVPixelBufferWidthKey as String: outW,
    kCVPixelBufferHeightKey as String: outH,
    kCVPixelBufferCGImageCompatibilityKey as String: true,
    kCVPixelBufferCGBitmapContextCompatibilityKey as String: true,
  ])
writer.add(input)
guard writer.startWriting() else { die("startWriting: \(writer.error?.localizedDescription ?? "?")") }
writer.startSession(atSourceTime: .zero)

// --- resample onto the time map ---
let demoOut = (doneAt - playAt) / speed
let duration = holdStart + demoOut + holdEnd
let total = Int((duration * Double(fps)).rounded(.up))

/// Output time -> source (capture) time.
func sourceTime(_ t: Double) -> Double {
  if t < holdStart { return playAt }  // landing hold
  return min(playAt + (t - holdStart) * speed, doneAt)  // demo, then final-state hold
}

var idx = 0
var cachedIdx = -1
var cached: CGImage = render(first)
for k in 0..<total {
  let src = sourceTime(Double(k) / Double(fps))
  while idx + 1 < frames.count && frames[idx + 1].t <= src { idx += 1 }
  if idx != cachedIdx {
    cached = idx == 0 ? cached : render(load(frames[idx]))
    cachedIdx = idx
  }

  while !input.isReadyForMoreMediaData { usleep(2000) }
  var pb: CVPixelBuffer?
  guard let pool = adaptor.pixelBufferPool,
    CVPixelBufferPoolCreatePixelBuffer(nil, pool, &pb) == kCVReturnSuccess, let buf = pb
  else { die("no pixel buffer") }
  CVPixelBufferLockBaseAddress(buf, [])
  let ctx = CGContext(
    data: CVPixelBufferGetBaseAddress(buf), width: outW, height: outH, bitsPerComponent: 8,
    bytesPerRow: CVPixelBufferGetBytesPerRow(buf), space: srgb, bitmapInfo: bitmapInfo)!
  ctx.draw(cached, in: CGRect(x: 0, y: 0, width: outW, height: outH))
  CVPixelBufferUnlockBaseAddress(buf, [])
  if !adaptor.append(buf, withPresentationTime: CMTime(value: CMTimeValue(k), timescale: fps)) {
    die("append failed at frame \(k): \(writer.error?.localizedDescription ?? "?")")
  }
}

input.markAsFinished()
let done = DispatchSemaphore(value: 0)
writer.finishWriting { done.signal() }
done.wait()
guard writer.status == .completed else { die("finishWriting: \(writer.error?.localizedDescription ?? "?")") }

// --- poster: the final, fully-booked state ---
if let posterPath {
  let lastIdx = frames.lastIndex { $0.t <= doneAt } ?? frames.count - 1
  let poster = render(load(frames[lastIdx]))
  let url = URL(fileURLWithPath: posterPath) as CFURL
  guard let dest = CGImageDestinationCreateWithURL(url, UTType.jpeg.identifier as CFString, 1, nil)
  else { die("can't write poster") }
  CGImageDestinationAddImage(dest, poster, [kCGImageDestinationLossyCompressionQuality: 0.88] as CFDictionary)
  CGImageDestinationFinalize(dest)
}

let bytes = (try? FileManager.default.attributesOfItem(atPath: outURL.path)[.size] as? Int) ?? 0
print(
  String(
    format: "  ✓ %@ — %dx%d (from %dx%d) · %.1fs · %.1f MB", outURL.lastPathComponent, outW, outH,
    first.width, cropH, duration, Double(bytes) / 1_048_576))
