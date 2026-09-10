import Foundation

struct ConjugationForm: Identifiable {
    let name: String
    let value: String

    var id: String { name }
}

struct ConjugationRule: Identifiable, Hashable {
    let title: String
    let category: String
    let formula: String
    let explanation: String
    let notes: [String]

    var id: String { "\(category)-\(title)" }
}

enum ConjugationRuleGuide {
    static func rule(for form: ConjugationForm, item: VocabularyItem) -> ConjugationRule {
        let category = item.conjugationTypeLabel
            ?? (item.adjectiveClass == "i" ? "い形容词" : "な形容词")
        let formula = formula(for: form.name, item: item)
        return ConjugationRule(
            title: form.name,
            category: category,
            formula: formula,
            explanation: explanation(for: form.name),
            notes: notes(for: form.name, item: item)
        )
    }

    private static func formula(for name: String, item: VocabularyItem) -> String {
        if item.posGroup == "adjective" {
            let isNa = item.adjectiveClass == "na" || item.partOfSpeech.contains("な形容词")
            if isNa {
                switch name {
                case "连用形": return "词干＋に"
                case "て形": return "词干＋で"
                case "ば形": return "词干＋であれば"
                case "简体形": return "词干＋だ"
                case "简体否定": return "词干＋ではない"
                case "简体过去": return "词干＋だった"
                case "简体过去否定": return "词干＋ではなかった"
                default: return "在形容词词干后接相应形式"
                }
            }
            switch name {
            case "连用形": return "去掉词尾「い」＋く"
            case "て形": return "去掉词尾「い」＋くて"
            case "ば形": return "去掉词尾「い」＋ければ"
            case "简体形": return "保留原形"
            case "简体否定": return "去掉词尾「い」＋くない"
            case "简体过去": return "去掉词尾「い」＋かった"
            case "简体过去否定": return "去掉词尾「い」＋くなかった"
            default: return "替换い形容词的词尾"
            }
        }

        let stem: String
        switch item.conjugationTypeLabel {
        case "一段动词": stem = "去掉词尾「る」"
        case "サ变动词": stem = "「する」按不规则形式变化"
        case "カ变动词": stem = "「くる／来る」按不规则形式变化"
        default: stem = "将五段动词词尾移到相应行"
        }
        switch name {
        case "连用形": return "\(stem)，使用连用形"
        case "ます形": return "连用形＋ます"
        case "て形": return item.verbClass == "godan" ? "按词尾发生音便＋て／で" : "\(stem)＋て"
        case "ない形": return item.verbClass == "godan" ? "词尾变为あ段＋ない（う→わ）" : "\(stem)＋ない"
        case "た形": return item.verbClass == "godan" ? "按て形音便，将て／で换为た／だ" : "\(stem)＋た"
        case "命令形": return item.verbClass == "godan" ? "词尾变为え段" : "\(stem)＋ろ"
        case "意志形": return item.verbClass == "godan" ? "词尾变为お段＋う" : "\(stem)＋よう"
        case "ば形": return item.verbClass == "godan" ? "词尾变为え段＋ば" : "\(stem)＋れば"
        case "可能形": return item.verbClass == "godan" ? "词尾变为え段＋る" : "\(stem)＋られる"
        case "被动形": return item.verbClass == "godan" ? "词尾变为あ段＋れる" : "\(stem)＋られる"
        case "使役形": return item.verbClass == "godan" ? "词尾变为あ段＋せる" : "\(stem)＋させる"
        case "使役被动形": return item.verbClass == "godan" ? "词尾变为あ段＋される" : "\(stem)＋させられる"
        case "たり形": return "た形＋り"
        case "たい形": return "连用形＋たい"
        case "なければ形": return "ない形去掉「い」＋ければ"
        default: return stem
        }
    }

    private static func explanation(for name: String) -> String {
        switch name {
        case "连用形": return "连接助动词或其他表达的基础形式，ます形和たい形等都由它构成。"
        case "ます形": return "动词的礼貌表达，用于较正式或需要礼貌的叙述。"
        case "て形": return "用于连接动作，也用于请求、进行、许可等大量句型。"
        case "ない形": return "表示动作或状态不发生的简体否定形式。"
        case "た形": return "表示完成或过去，也用于经验、列举等句型。"
        case "命令形": return "直接要求对方采取行动，语气较强，使用时需要注意场合。"
        case "意志形": return "表示说话人的意志，也可用于提议“一起做……”。"
        case "ば形": return "表示假定条件，相当于“如果……的话”。"
        case "可能形": return "表示具备做某事的能力或某事有可能实现。"
        case "被动形": return "表示主语承受他人的动作，也用于受害被动等表达。"
        case "使役形": return "表示让、使或允许他人做某事。"
        case "使役被动形": return "表示被迫或被要求做某事。"
        case "たり形": return "与「たりする」搭配，列举若干代表性动作或状态。"
        case "たい形": return "表示说话人想做某事的愿望。"
        case "なければ形": return "表示“不……的话”，也常用于义务表达「なければならない」。"
        case "简体形": return "用于普通体叙述，也可放在名词前修饰名词。"
        case "简体否定": return "形容词在普通体中的现在否定形式。"
        case "简体过去": return "形容词在普通体中的过去肯定形式。"
        case "简体过去否定": return "形容词在普通体中的过去否定形式。"
        default: return "这是日语活用体系中的一种连接或句法形式。"
        }
    }

    private static func notes(for name: String, item: VocabularyItem) -> [String] {
        var result: [String] = []
        if item.word == "行く" && (name == "て形" || name == "た形") {
            result.append("「行く」是特殊音便：て形为「行って」，た形为「行った」。")
        }
        if item.word == "ある" && (name == "ない形" || name == "なければ形") {
            result.append("「ある」的否定使用「ない」，不是「あらない」。")
        }
        if (item.word == "いい" || item.word == "良い") && item.posGroup == "adjective" {
            result.append("「いい／良い」活用时使用词干「よ」，例如「よくない」「よかった」。")
        }
        if name == "可能形" && item.verbClass == "ichidan" {
            result.append("口语中也常见省略「ら」的形式，但规范形式为「られる」。")
        }
        return result
    }
}

enum JapaneseConjugator {
    static func forms(for item: VocabularyItem) -> [ConjugationForm] {
        if item.posGroup == "verb" {
            return verbForms(for: item)
        }
        if item.posGroup == "adjective" {
            return adjectiveForms(for: item)
        }
        return []
    }

    private static func verbForms(for item: VocabularyItem) -> [ConjugationForm] {
        let word = item.word
        let pos = item.primaryPartOfSpeech.lowercased()

        // The surface form is authoritative for する compounds. This also
        // protects against an occasional ambiguous JMdict match for する.
        if word.hasSuffix("する") {
            return suruForms(prefix: String(word.dropLast(2)))
        }

        if item.verbClass == "ichidan" {
            guard word.hasSuffix("る") else { return [] }
            let stem = String(word.dropLast())
            return standardVerbForms(
                continuative: stem,
                masu: stem + "ます",
                te: stem + "て",
                nai: stem + "ない",
                ta: stem + "た",
                imperative: stem + "ろ",
                volitional: stem + "よう",
                conditional: stem + "れば",
                potential: stem + "られる",
                passive: stem + "られる",
                causative: stem + "させる",
                causativePassive: stem + "させられる",
                tari: stem + "たり",
                tai: stem + "たい",
                nakereba: stem + "なければ"
            )
        }

        if item.verbClass == "irregular" || pos.contains("suru verb") || pos.contains("kuru verb") {
            if pos.contains("suru verb") {
                return suruForms(prefix: "")
            }
            if word.hasSuffix("来る") || pos.contains("kuru verb") {
                let prefix = word.hasSuffix("来る") ? String(word.dropLast(2)) : ""
                return kuruForms(prefix: prefix, usesKanji: word.hasSuffix("来る"))
            }
            if word.hasSuffix("くる") {
                return kuruForms(prefix: String(word.dropLast(2)), usesKanji: false)
            }
        }

        guard item.verbClass == "godan", let ending = word.last else { return [] }
        if word == "ある" {
            return standardVerbForms(
                continuative: "あり", masu: "あります", te: "あって", nai: "ない", ta: "あった",
                imperative: "あれ", volitional: "あろう", conditional: "あれば", potential: "あり得る",
                passive: "あられる", causative: "あらせる", causativePassive: "あらされる",
                tari: "あったり", tai: "ありたい", nakereba: "なければ"
            )
        }

        let stem = String(word.dropLast())
        guard let row = godanRow(for: ending) else { return [] }
        let te = word == "行く" ? stem + "って" : stem + row.te
        let ta = word == "行く" ? stem + "った" : stem + row.ta
        return standardVerbForms(
            continuative: stem + row.i,
            masu: stem + row.i + "ます",
            te: te,
            nai: stem + row.a + "ない",
            ta: ta,
            imperative: stem + row.e,
            volitional: stem + row.o + "う",
            conditional: stem + row.e + "ば",
            potential: stem + row.e + "る",
            passive: stem + row.a + "れる",
            causative: stem + row.a + "せる",
            causativePassive: stem + row.a + "される",
            tari: ta + "り",
            tai: stem + row.i + "たい",
            nakereba: stem + row.a + "なければ"
        )
    }

    private static func adjectiveForms(for item: VocabularyItem) -> [ConjugationForm] {
        let word = item.word
        let isNaAdjective = item.partOfSpeech.contains("な形容词")
            || item.adjectiveClass == "na"
            || item.primaryPartOfSpeech.lowercased().contains("quasi-adjective")

        if isNaAdjective {
            let stem = word.hasSuffix("だ") ? String(word.dropLast()) : word
            return [
                .init(name: "连用形", value: stem + "に"),
                .init(name: "て形", value: stem + "で"),
                .init(name: "ば形", value: stem + "であれば"),
                .init(name: "简体形", value: stem + "だ"),
                .init(name: "简体否定", value: stem + "ではない"),
                .init(name: "简体过去", value: stem + "だった"),
                .init(name: "简体过去否定", value: stem + "ではなかった")
            ]
        }

        guard item.adjectiveClass == "i" || item.partOfSpeech.contains("い形容词") else { return [] }
        if word == "いい" || word == "良い" {
            return adjectiveIForms(dictionary: word, stem: "よ")
        }
        guard word.hasSuffix("い") else { return [] }
        return adjectiveIForms(dictionary: word, stem: String(word.dropLast()))
    }

    private static func adjectiveIForms(dictionary: String, stem: String) -> [ConjugationForm] {
        [
            .init(name: "连用形", value: stem + "く"),
            .init(name: "て形", value: stem + "くて"),
            .init(name: "ば形", value: stem + "ければ"),
            .init(name: "简体形", value: dictionary),
            .init(name: "简体否定", value: stem + "くない"),
            .init(name: "简体过去", value: stem + "かった"),
            .init(name: "简体过去否定", value: stem + "くなかった")
        ]
    }

    private static func suruForms(prefix: String) -> [ConjugationForm] {
        standardVerbForms(
            continuative: prefix + "し", masu: prefix + "します", te: prefix + "して",
            nai: prefix + "しない", ta: prefix + "した", imperative: prefix + "しろ",
            volitional: prefix + "しよう", conditional: prefix + "すれば", potential: prefix + "できる",
            passive: prefix + "される", causative: prefix + "させる", causativePassive: prefix + "させられる",
            tari: prefix + "したり", tai: prefix + "したい", nakereba: prefix + "しなければ"
        )
    }

    private static func kuruForms(prefix: String, usesKanji: Bool) -> [ConjugationForm] {
        let ki = usesKanji ? prefix + "来" : prefix + "き"
        let ko = usesKanji ? prefix + "来" : prefix + "こ"
        let ku = usesKanji ? prefix + "来" : prefix + "く"
        return standardVerbForms(
            continuative: ki, masu: ki + "ます", te: ki + "て", nai: ko + "ない", ta: ki + "た",
            imperative: ko + "い", volitional: ko + "よう", conditional: ku + "れば",
            potential: ko + "られる", passive: ko + "られる", causative: ko + "させる",
            causativePassive: ko + "させられる", tari: ki + "たり", tai: ki + "たい",
            nakereba: ko + "なければ"
        )
    }

    private static func standardVerbForms(
        continuative: String, masu: String, te: String, nai: String, ta: String,
        imperative: String, volitional: String, conditional: String, potential: String,
        passive: String, causative: String, causativePassive: String,
        tari: String, tai: String, nakereba: String
    ) -> [ConjugationForm] {
        [
            .init(name: "连用形", value: continuative), .init(name: "ます形", value: masu),
            .init(name: "て形", value: te), .init(name: "ない形", value: nai),
            .init(name: "た形", value: ta), .init(name: "命令形", value: imperative),
            .init(name: "意志形", value: volitional), .init(name: "ば形", value: conditional),
            .init(name: "可能形", value: potential), .init(name: "被动形", value: passive),
            .init(name: "使役形", value: causative), .init(name: "使役被动形", value: causativePassive),
            .init(name: "たり形", value: tari), .init(name: "たい形", value: tai),
            .init(name: "なければ形", value: nakereba)
        ]
    }

    private static func godanRow(for ending: Character) -> (a: String, i: String, e: String, o: String, te: String, ta: String)? {
        switch ending {
        case "う": ("わ", "い", "え", "お", "って", "った")
        case "つ": ("た", "ち", "て", "と", "って", "った")
        case "る": ("ら", "り", "れ", "ろ", "って", "った")
        case "ぶ": ("ば", "び", "べ", "ぼ", "んで", "んだ")
        case "む": ("ま", "み", "め", "も", "んで", "んだ")
        case "ぬ": ("な", "に", "ね", "の", "んで", "んだ")
        case "く": ("か", "き", "け", "こ", "いて", "いた")
        case "ぐ": ("が", "ぎ", "げ", "ご", "いで", "いだ")
        case "す": ("さ", "し", "せ", "そ", "して", "した")
        default: nil
        }
    }
}
