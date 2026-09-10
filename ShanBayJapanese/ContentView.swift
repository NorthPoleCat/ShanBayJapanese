//
//  ContentView.swift
//  ShanBayJapanese
//
//  Created by xun liu on 2026/9/7.
//

import SwiftUI
import AVFoundation

struct ContentView: View {
    private let repository: VocabularyRepository?
    private let databaseError: String?

    init() {
        do {
            repository = try VocabularyRepository()
            databaseError = nil
        } catch {
            repository = nil
            databaseError = error.localizedDescription
        }
    }

    var body: some View {
        NavigationStack {
            if let databaseError {
                ContentUnavailableView(
                    "词库不可用",
                    systemImage: "exclamationmark.triangle",
                    description: Text(databaseError)
                )
            } else {
                ScrollView {
                    LazyVGrid(
                        columns: [GridItem(.adaptive(minimum: 150), spacing: 14)],
                        spacing: 14
                    ) {
                        ForEach(VocabularyEntrance.allCases) { entrance in
                            NavigationLink {
                                VocabularyListView(
                                    entrance: entrance,
                                    repository: repository
                                )
                            } label: {
                                VocabularyEntranceCard(entrance: entrance)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .padding(16)
                }
                .background(Color(uiColor: .systemGroupedBackground))
                .navigationTitle("日语词库")
            }
        }
    }
}

private enum VocabularyEntrance: Int, CaseIterable, Identifiable {
    case all = 0, n5 = 5, n4 = 4, n3 = 3, n2 = 2, n1 = 1

    var id: Int { rawValue }
    var level: Int? { self == .all ? nil : rawValue }
    var title: String { self == .all ? "全部单词" : "N\(rawValue)" }

    var subtitle: String {
        switch self {
        case .all: "浏览完整词库"
        case .n5: "入门基础"
        case .n4: "初级词汇"
        case .n3: "中级词汇"
        case .n2: "中高级词汇"
        case .n1: "高级词汇"
        }
    }

    var systemImage: String { self == .all ? "books.vertical.fill" : "character.book.closed.fill" }

    var color: Color {
        switch self {
        case .all: .indigo
        case .n5: .green
        case .n4: .teal
        case .n3: .blue
        case .n2: .orange
        case .n1: .red
        }
    }
}

private struct VocabularyEntranceCard: View {
    let entrance: VocabularyEntrance

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Image(systemName: entrance.systemImage)
                .font(.title2)
                .foregroundStyle(entrance.color)
                .frame(width: 42, height: 42)
                .background(entrance.color.opacity(0.12), in: RoundedRectangle(cornerRadius: 11))

            VStack(alignment: .leading, spacing: 4) {
                Text(entrance.title)
                    .font(.headline)
                Text(entrance.subtitle)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity, minHeight: 118, alignment: .leading)
        .padding(16)
        .background(Color(uiColor: .secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 16))
    }
}

private struct VocabularyListView: View {
    let entrance: VocabularyEntrance
    let repository: VocabularyRepository?

    @State private var searchText = ""
    @State private var words: [VocabularyItem] = []
    @State private var errorMessage: String?

    var body: some View {
        Group {
            if let errorMessage {
                ContentUnavailableView(
                    "查询失败",
                    systemImage: "exclamationmark.triangle",
                    description: Text(errorMessage)
                )
            } else if words.isEmpty {
                ContentUnavailableView.search(text: searchText)
            } else {
                List(words) { item in
                    NavigationLink {
                        VocabularyDetailView(item: item, repository: repository)
                    } label: {
                        VocabularyRow(item: item)
                    }
                }
                .listStyle(.plain)
            }
        }
        .navigationTitle(entrance.title)
        .navigationBarTitleDisplayMode(.inline)
        .searchable(text: $searchText, prompt: "日文、假名或释义")
        .onSubmit(of: .search, runSearch)
        .onChange(of: searchText) { _, _ in runSearch() }
        .task { runSearch() }
    }

    private func runSearch() {
        guard let repository else { return }
        do {
            words = try repository.search(text: searchText, level: entrance.level, limit: 10_000)
            errorMessage = nil
        } catch {
            words = []
            errorMessage = error.localizedDescription
        }
    }
}

private struct VocabularyDetailView: View {
    @Environment(\.colorScheme) private var colorScheme
    @Environment(\.dismiss) private var dismiss

    let item: VocabularyItem
    let repository: VocabularyRepository?

    @State private var senses: [VocabularySense] = []
    @State private var examples: [VocabularyExample] = []
    @State private var spellings: [VocabularySpelling] = []
    @State private var errorMessage: String?
    @State private var isMeaningsExpanded = true
    @State private var isConjugationsExpanded = true
    @State private var speechSynthesizer = AVSpeechSynthesizer()

    private var conjugations: [ConjugationForm] {
        JapaneseConjugator.forms(for: item)
    }

    private var kanjiSpellings: [String] {
        Array(spellings.filter { $0.type == "kanji" || $0.type == "mixed" }.prefix(1)).map(\.spelling)
    }

    private var kanaSpellings: [String] {
        spellings.filter { $0.type == "kana" }.map(\.spelling)
    }

    private var themeColor: Color {
        colorScheme == .dark
            ? Color(red: 0.4, green: 0.7, blue: 1.0)
            : Color(red: 0.2, green: 0.6, blue: 1.0)
    }

    var body: some View {
        VStack(spacing: 0) {
            detailHeader

            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    HStack(alignment: .firstTextBaseline, spacing: 8) {
                        Text(item.word)
                            .font(.title2.bold())
                        if !item.reading.isEmpty && item.reading != item.word {
                            Text("（\(item.reading)）")
                                .font(.body)
                                .foregroundStyle(.secondary)
                        }
                    }
                    .padding(.bottom, 10)

                    if !kanjiSpellings.isEmpty {
                        VStack(alignment: .leading, spacing: 6) {
                            spellingRow(label: "汉字", values: kanjiSpellings)
                            spellingRow(
                                label: "假名",
                                values: kanaSpellings.isEmpty ? [item.reading] : kanaSpellings
                            )
                        }
                        .padding(.bottom, 12)
                    }

                    VStack(alignment: .leading, spacing: 8) {
                        HStack(spacing: 8) {
                            ForEach(Array(item.partOfSpeechLabels.enumerated()), id: \.offset) { index, label in
                                detailTag(label, color: partOfSpeechTagColor(at: index))
                            }
                        }

                        HStack(spacing: 8) {
                            detailTag("JLPT N\(item.level)", color: themeColor)
                            if item.isCommon {
                                detailTag("常用", color: .orange, systemImage: "star.fill")
                            }
                        }
                    }

                    Divider()
                        .padding(.vertical, 16)

                    meaningsView

                    Divider()
                        .padding(.vertical, 16)

                    if !conjugations.isEmpty {
                        conjugationsView
                        Divider()
                            .padding(.vertical, 16)
                    }

                    examplesView

                    if let errorMessage {
                        Label(errorMessage, systemImage: "exclamationmark.triangle")
                            .font(.footnote)
                            .foregroundStyle(.red)
                            .padding(.top, 16)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal, 16)
                .padding(.vertical, 18)
            }
        }
        .background(Color(uiColor: .systemBackground))
        .toolbar(.hidden, for: .navigationBar)
        .task { loadDetails() }
        .onDisappear {
            speechSynthesizer.stopSpeaking(at: .immediate)
        }
    }

    private var detailHeader: some View {
        HStack {
            Button {
                dismiss()
            } label: {
                Image(systemName: "chevron.left")
                    .font(.headline)
                    .frame(width: 44, height: 44)
            }

            Spacer()

            Text("单词详情")
                .font(.headline)

            Spacer()

            Button {
                playAudio()
            } label: {
                Image(systemName: "speaker.wave.2.fill")
                    .font(.headline)
                    .frame(width: 44, height: 44)
            }
        }
        .foregroundStyle(.white)
        .padding(.horizontal, 4)
        .background(themeColor.ignoresSafeArea(edges: .top))
    }

    @ViewBuilder
    private var meaningsView: some View {
        VStack(alignment: .leading, spacing: 10) {
            collapsibleHeader(
                title: "释义",
                detail: senses.isEmpty ? nil : "\(senses.count)项",
                isExpanded: $isMeaningsExpanded
            )

            if isMeaningsExpanded {
                Group {
                    if senses.isEmpty {
                        Text("暂无释义")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(senses) { sense in
                            VStack(alignment: .leading, spacing: 4) {
                                HStack(alignment: .firstTextBaseline, spacing: 6) {
                                    if senses.count > 1 {
                                        Text("\(sense.index + 1).")
                                            .foregroundStyle(.secondary)
                                    }
                                    Text(sense.meaningChinese.isEmpty ? sense.meaningEnglish : sense.meaningChinese)
                                }
                                if !sense.meaningChinese.isEmpty && !sense.meaningEnglish.isEmpty {
                                    Text(sense.meaningEnglish)
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                        .padding(.leading, senses.count > 1 ? 20 : 0)
                                }
                            }
                        }
                    }
                }
                .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
    }

    private var conjugationsView: some View {
        VStack(alignment: .leading, spacing: 10) {
            collapsibleHeader(
                title: "变形",
                detail: "\(conjugations.count)种",
                isExpanded: $isConjugationsExpanded
            )

            if isConjugationsExpanded {
                ForEach(conjugations) { form in
                    NavigationLink {
                        ConjugationRuleView(
                            item: item,
                            form: form,
                            rule: ConjugationRuleGuide.rule(for: form, item: item)
                        )
                    } label: {
                        HStack(alignment: .firstTextBaseline, spacing: 12) {
                            HStack(spacing: 5) {
                                Text(form.name)
                                Image(systemName: "chevron.right")
                                    .font(.caption2.bold())
                            }
                            .font(.subheadline)
                            .padding(.vertical, 4)
                            .padding(.horizontal, 7)
                            .foregroundStyle(.white)
                            .background(themeColor, in: RoundedRectangle(cornerRadius: 5))
                            Spacer()
                            Text(form.value)
                                .font(.body.weight(.medium))
                                .foregroundStyle(.primary)
                                .multilineTextAlignment(.trailing)
                        }
                    }
                    .buttonStyle(.plain)
                }
                .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
    }

    private func collapsibleHeader(
        title: String,
        detail: String?,
        isExpanded: Binding<Bool>
    ) -> some View {
        Button {
            withAnimation(.easeInOut(duration: 0.2)) {
                isExpanded.wrappedValue.toggle()
            }
        } label: {
            HStack {
                Text(title)
                    .font(.headline)
                    .foregroundStyle(themeColor)
                Spacer()
                if let detail {
                    Text(detail)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Image(systemName: isExpanded.wrappedValue ? "chevron.up" : "chevron.down")
                    .font(.caption.bold())
                    .foregroundStyle(themeColor)
            }
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }

    @ViewBuilder
    private var examplesView: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("例句")
                .font(.headline)
                .foregroundStyle(themeColor)

            if examples.isEmpty {
                Text("这个词目前没有收录例句")
                    .foregroundStyle(.secondary)
            } else {
                ForEach(Array(examples.enumerated()), id: \.element.id) { index, example in
                    VStack(alignment: .leading, spacing: 7) {
                        Text(example.sentenceJapanese)
                            .font(.body)
                        if !example.sentenceChinese.isEmpty {
                            Text(example.sentenceChinese)
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                        if !example.sentenceEnglish.isEmpty {
                            Text(example.sentenceEnglish)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)

                    if index < examples.count - 1 {
                        Divider()
                    }
                }
            }
        }
    }

    private func detailTag(_ title: String, color: Color, systemImage: String? = nil) -> some View {
        HStack(spacing: 4) {
            if let systemImage {
                Image(systemName: systemImage)
            }
            Text(title)
        }
        .font(.caption)
        .padding(.vertical, 4)
        .padding(.horizontal, 7)
        .foregroundStyle(.white)
        .background(color, in: RoundedRectangle(cornerRadius: 5))
    }

    private func spellingRow(label: String, values: [String]) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 10) {
            Text(label)
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)
                .frame(width: 34, alignment: .leading)
            Text(values.filter { !$0.isEmpty }.joined(separator: "、"))
                .font(.subheadline)
                .textSelection(.enabled)
        }
    }

    private var partOfSpeechColor: Color {
        switch item.posGroup {
        case "verb": Color(red: 0.91, green: 0.42, blue: 0.54)
        case "adjective": Color(red: 0.33, green: 0.72, blue: 0.52)
        default: .gray
        }
    }

    private func partOfSpeechTagColor(at index: Int) -> Color {
        if item.posGroup == "verb" && index == 1 {
            return Color(red: 0.2, green: 0.4, blue: 0.8)
        }
        return partOfSpeechColor
    }

    private func playAudio() {
        let target = item.word.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !target.isEmpty else { return }
        speechSynthesizer.stopSpeaking(at: .immediate)
        let utterance = AVSpeechUtterance(string: target)
        utterance.voice = AVSpeechSynthesisVoice(language: "ja-JP")
        utterance.rate = 0.46
        speechSynthesizer.speak(utterance)
    }

    private func loadDetails() {
        guard let repository else { return }
        do {
            senses = try repository.senses(for: item.id)
            examples = try repository.examples(for: item.id)
            spellings = try repository.spellings(for: item.id)
            errorMessage = nil
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

private struct ConjugationRuleView: View {
    @Environment(\.colorScheme) private var colorScheme
    @Environment(\.dismiss) private var dismiss

    let item: VocabularyItem
    let form: ConjugationForm
    let rule: ConjugationRule

    private var themeColor: Color {
        colorScheme == .dark
            ? Color(red: 0.4, green: 0.7, blue: 1.0)
            : Color(red: 0.2, green: 0.6, blue: 1.0)
    }

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Button { dismiss() } label: {
                    Image(systemName: "chevron.left")
                        .font(.headline)
                        .frame(width: 44, height: 44)
                }
                Spacer()
                Text("变形规则")
                    .font(.headline)
                Spacer()
                Color.clear.frame(width: 44, height: 44)
            }
            .foregroundStyle(.white)
            .padding(.horizontal, 4)
            .background(themeColor.ignoresSafeArea(edges: .top))

            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text(rule.title)
                            .font(.title2.bold())
                        Text(rule.category)
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(themeColor)
                    }

                    ruleSection(title: "当前单词") {
                        HStack(spacing: 10) {
                            Text(item.word)
                            Image(systemName: "arrow.right")
                                .foregroundStyle(.secondary)
                            Text(form.value)
                                .fontWeight(.semibold)
                                .foregroundStyle(themeColor)
                        }
                        .font(.title3)
                        .textSelection(.enabled)
                    }

                    ruleSection(title: "构成规则") {
                        Text(rule.formula)
                            .font(.body.weight(.medium))
                    }

                    ruleSection(title: "用法") {
                        Text(rule.explanation)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    if !rule.notes.isEmpty {
                        ruleSection(title: "注意") {
                            VStack(alignment: .leading, spacing: 8) {
                                ForEach(rule.notes, id: \.self) { note in
                                    Label(note, systemImage: "exclamationmark.circle")
                                        .fixedSize(horizontal: false, vertical: true)
                                }
                            }
                        }
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(18)
            }
        }
        .background(Color(uiColor: .systemBackground))
        .toolbar(.hidden, for: .navigationBar)
    }

    private func ruleSection<Content: View>(
        title: String,
        @ViewBuilder content: () -> Content
    ) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(title)
                .font(.headline)
                .foregroundStyle(themeColor)
            content()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(Color(uiColor: .secondarySystemBackground), in: RoundedRectangle(cornerRadius: 12))
    }
}

private struct VocabularyRow: View {
    let item: VocabularyItem

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            HStack(alignment: .firstTextBaseline) {
                Text(item.word)
                    .font(.title3.weight(.semibold))

                if !item.reading.isEmpty && item.reading != item.word {
                    Text(item.reading)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                Spacer()

                Text("N\(item.level)")
                    .font(.caption.bold())
                    .foregroundStyle(levelColor)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(levelColor.opacity(0.12), in: Capsule())
            }

            if !item.meanings.isEmpty {
                Text(item.meanings)
                    .font(.subheadline)
                    .foregroundStyle(.primary)
                    .lineLimit(3)
            }

            HStack(spacing: 8) {
                if !item.partOfSpeechLabels.isEmpty {
                    Text(item.partOfSpeechLabels.joined(separator: " · "))
                }
                if item.isCommon {
                    Label("常用", systemImage: "star.fill")
                }
            }
            .font(.caption)
            .foregroundStyle(.secondary)
        }
        .padding(.vertical, 5)
    }

    private var levelColor: Color {
        switch item.level {
        case 5: .green
        case 4: .teal
        case 3: .blue
        case 2: .orange
        default: .red
        }
    }
}
