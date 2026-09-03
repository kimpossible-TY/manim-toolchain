// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "RenderPulse",
    platforms: [.macOS(.v14)],
    products: [
        .executable(name: "RenderPulse", targets: ["RenderPulse"]),
    ],
    targets: [
        .executableTarget(name: "RenderPulse"),
        .testTarget(name: "RenderPulseTests", dependencies: ["RenderPulse"]),
    ]
)
