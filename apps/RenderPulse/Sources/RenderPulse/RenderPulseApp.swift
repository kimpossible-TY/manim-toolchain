import AppKit
import SwiftUI

@main
struct RenderPulseApp: App {
    @StateObject private var store: WorkMonitorStore

    init() {
        NSApplication.shared.setActivationPolicy(.accessory)
        _store = StateObject(wrappedValue: WorkMonitorStore())
    }

    var body: some Scene {
        MenuBarExtra {
            MonitorPopover(store: store)
                .task { store.start() }
        } label: {
            MenuBarLabel(
                primaryWork: store.primaryWork,
                additionalActiveWorkCount: store.additionalActiveWorkCount
            )
            .task { store.start() }
        }
        .menuBarExtraStyle(.window)
    }
}

private struct MenuBarLabel: View {
    let primaryWork: WorkRuntime?
    let additionalActiveWorkCount: Int

    var body: some View {
        HStack(spacing: 4) {
            Image(systemName: symbolName)
                .foregroundStyle(tint)

            if let primaryWork {
                Text(compactName(primaryWork.configuration.name))
                    .lineLimit(1)
                if primaryWork.snapshot != nil {
                    Text("\(primaryWork.percent, format: .number.precision(.fractionLength(0)))%")
                        .monospacedDigit()
                }
            } else {
                Text("RenderPulse")
            }

            if additionalActiveWorkCount > 0 {
                Text("+\(additionalActiveWorkCount)")
                    .foregroundStyle(.secondary)
            }
        }
        .accessibilityLabel(accessibilityDescription)
    }

    private var symbolName: String {
        guard let state = primaryWork?.state else { return "gearshape" }
        switch state {
        case .completed: return "checkmark.circle.fill"
        case .error: return "exclamationmark.triangle.fill"
        default: return "gearshape.fill"
        }
    }

    private var tint: Color {
        guard let work = primaryWork else { return .secondary }
        if (work.snapshot?.errors.count ?? 0) > 0 { return .red }
        if (work.snapshot?.warnings.count ?? 0) > 0 { return .yellow }
        switch work.state {
        case .completed: return .green
        case .error: return .red
        case .queued, .waiting: return .secondary
        case .running: return Color.accentColor
        case nil: return .secondary
        }
    }

    private var accessibilityDescription: String {
        guard let primaryWork else { return "RenderPulse. No registered work." }
        return "\(primaryWork.configuration.name), \(primaryWork.state?.label ?? "Unavailable"), \(primaryWork.percent.formatted(.number.precision(.fractionLength(0)))) percent"
    }

    private func compactName(_ name: String) -> String {
        let limit = 20
        guard name.count > limit else { return name }
        return "\(name.prefix(limit - 1))…"
    }
}
