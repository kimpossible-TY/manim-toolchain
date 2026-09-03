import AppKit
import SwiftUI

struct MonitorPopover: View {
    @ObservedObject var store: WorkMonitorStore

    @State private var showingAddWork = false
    @State private var pendingRemoval: WorkRuntime?

    var body: some View {
        VStack(spacing: 0) {
            header

            if store.works.isEmpty {
                ContentUnavailableView(
                    "No work yet",
                    systemImage: "gearshape",
                    description: Text("Add a RunPod jobs file to begin monitoring it.")
                )
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollView {
                    LazyVStack(spacing: 10) {
                        ForEach(store.orderedWorks) { work in
                            WorkCard(
                                work: work,
                                isPrimary: work.id == store.primaryWork?.id,
                                onSelect: { store.selectWork(id: work.id) },
                                onRemove: { pendingRemoval = work }
                            )
                        }
                    }
                    .padding(14)
                }
            }

            Divider()
            footer
        }
        .frame(width: 390, height: store.works.isEmpty ? 270 : 480)
        .sheet(isPresented: $showingAddWork) {
            AddWorkSheet { name, jobsFilePath in
                store.addWork(name: name, jobsFilePath: jobsFilePath)
            }
        }
        .alert(
            "Remove this work?",
            isPresented: Binding(
                get: { pendingRemoval != nil },
                set: { if !$0 { pendingRemoval = nil } }
            ),
            presenting: pendingRemoval
        ) { work in
            Button("Remove", role: .destructive) {
                store.removeWork(id: work.id)
                pendingRemoval = nil
            }
            Button("Cancel", role: .cancel) { pendingRemoval = nil }
        } message: { work in
            Text("\(work.configuration.name) will be removed from RenderPulse. Its RunPod job and render files will remain untouched.")
        }
    }

    private var header: some View {
        HStack(spacing: 10) {
            Image(systemName: "gearshape.fill")
                .foregroundStyle(Color.accentColor)
            Text("RenderPulse")
                .font(.headline)
            Spacer()
            if store.isRefreshing {
                ProgressView()
                    .controlSize(.small)
                    .accessibilityLabel("Refreshing work status")
            }
            Button {
                Task { await store.refresh() }
            } label: {
                Image(systemName: "arrow.clockwise")
            }
            .buttonStyle(.borderless)
            .help("Refresh now")

            Button {
                showingAddWork = true
            } label: {
                Image(systemName: "plus")
            }
            .buttonStyle(.borderless)
            .help("Add work")
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 13)
    }

    private var footer: some View {
        HStack {
            let activeCount = store.works.filter(\.isActive).count
            Text(activeCount == 1 ? "1 active work" : "\(activeCount) active works")
                .foregroundStyle(.secondary)
            Spacer()
            Button("Quit") {
                NSApplication.shared.terminate(nil)
            }
            .buttonStyle(.borderless)
        }
        .font(.footnote)
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
    }
}

private struct WorkCard: View {
    let work: WorkRuntime
    let isPrimary: Bool
    let onSelect: () -> Void
    let onRemove: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 11) {
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                VStack(alignment: .leading, spacing: 3) {
                    Text(work.configuration.name)
                        .font(.headline)
                        .lineLimit(1)
                    Text(statusText)
                        .font(.caption)
                        .foregroundStyle(statusTint)
                }
                Spacer(minLength: 4)
                Text("\(work.percent, format: .number.precision(.fractionLength(0)))%")
                    .font(.title3.weight(.semibold))
                    .monospacedDigit()
            }

            ProgressView(value: min(max(work.percent, 0), 100), total: 100)
                .tint(statusTint)

            LazyVGrid(
                columns: [GridItem(.flexible()), GridItem(.flexible())],
                alignment: .leading,
                spacing: 8
            ) {
                MetricRow(
                    title: "Pods",
                    value: workersText,
                    systemImage: "cpu",
                    tint: .primary
                )
                MetricRow(
                    title: "Warning",
                    value: "\(work.snapshot?.warnings.count ?? 0)",
                    systemImage: "exclamationmark.circle",
                    tint: (work.snapshot?.warnings.count ?? 0) > 0 ? .yellow : .secondary
                )
                MetricRow(
                    title: "Error",
                    value: "\(work.snapshot?.errors.count ?? 0)",
                    systemImage: "xmark.octagon",
                    tint: (work.snapshot?.errors.count ?? 0) > 0 ? .red : .secondary
                )
                MetricRow(
                    title: "ETA",
                    value: ETAFormatter.string(for: work.eta),
                    systemImage: "clock",
                    tint: .secondary
                )
            }

            if work.lastRefreshError {
                Label("Latest status refresh failed", systemImage: "wifi.exclamationmark")
                    .font(.caption)
                    .foregroundStyle(.orange)
            }

            HStack {
                Spacer()
                Button(action: onSelect) {
                    Label(isPrimary ? "Current" : "Show in menu bar", systemImage: isPrimary ? "pin.fill" : "pin")
                }
                .buttonStyle(.borderless)
                .font(.caption)
                .foregroundStyle(isPrimary ? Color.accentColor : .secondary)

                Button(role: .destructive, action: onRemove) {
                    Image(systemName: "trash")
                }
                .buttonStyle(.borderless)
                .help("Remove from RenderPulse")
            }
        }
        .padding(13)
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 13, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 13, style: .continuous)
                .stroke(isPrimary ? statusTint.opacity(0.45) : .clear, lineWidth: 1)
        }
    }

    private var statusText: String {
        work.state?.label ?? "Awaiting first refresh"
    }

    private var workersText: String {
        guard let workers = work.snapshot?.workers else { return "—" }
        return "\(workers.active) / \(workers.total)"
    }

    private var statusTint: Color {
        if (work.snapshot?.errors.count ?? 0) > 0 { return .red }
        if (work.snapshot?.warnings.count ?? 0) > 0 { return .yellow }
        switch work.state {
        case .running: return Color.accentColor
        case .completed: return .green
        case .error: return .red
        case .queued, .waiting, nil: return .secondary
        }
    }
}

private struct MetricRow: View {
    let title: String
    let value: String
    let systemImage: String
    let tint: Color

    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: systemImage)
                .foregroundStyle(tint)
                .frame(width: 14)
            VStack(alignment: .leading, spacing: 1) {
                Text(title)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                Text(value)
                    .font(.caption.weight(.medium))
                    .monospacedDigit()
                    .lineLimit(1)
            }
        }
    }
}
