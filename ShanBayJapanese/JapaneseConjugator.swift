import Foundation

struct ConjugationForm: Identifiable {
    let name: String
    let value: String

    var id: String { name }
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
