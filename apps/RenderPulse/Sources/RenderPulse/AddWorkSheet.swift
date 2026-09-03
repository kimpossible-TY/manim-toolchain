import AppKit
import SwiftUI
import UniformTypeIdentifiers

struct AddWorkSheet: View {
    @Environment(\.dismiss) private var dismiss

    @State private var name = ""
    @State private var jobsFilePath = ""

    let onAdd: (String, String) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            Text("Add Work")
                .font(.title2.weight(.semibold))

            Text("A work is one user-visible render operation. RenderPulse will aggregate all of its internal RunPod jobs into one progress view.")
                .font(.callout)
                .foregroundStyle(.secondary)

            Form {
                TextField("Work name", text: $name)

                HStack {
                    Text(jobsFilePath.isEmpty ? "No RunPod jobs file selected" : jobsFilePath)
                        .lineLimit(1)
                        .truncationMode(.middle)
                        .foregroundStyle(jobsFilePath.isEmpty ? .secondary : .primary)
                    Spacer()
                    Button("Choose…", action: chooseJobsFile)
                }
            }
            .formStyle(.grouped)

            HStack {
                Spacer()
                Button("Cancel") { dismiss() }
                    .keyboardShortcut(.cancelAction)
                Button("Add Work") {
                    onAdd(name.trimmingCharacters(in: .whitespacesAndNewlines), jobsFilePath)
                    dismiss()
                }
                .keyboardShortcut(.defaultAction)
                .disabled(name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || jobsFilePath.isEmpty)
            }
        }
        .padding(22)
        .frame(width: 480)
    }

    private func chooseJobsFile() {
        let panel = NSOpenPanel()
        panel.title = "Choose RunPod jobs file"
        panel.message = "Select the runpod.jobs.json file for the work you want to monitor."
        panel.allowedContentTypes = [.json]
        panel.canChooseDirectories = false
        panel.canChooseFiles = true
        panel.allowsMultipleSelection = false
        guard panel.runModal() == .OK, let url = panel.url else { return }

        jobsFilePath = url.path
        if name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            name = url.deletingLastPathComponent().lastPathComponent
        }
    }
}
