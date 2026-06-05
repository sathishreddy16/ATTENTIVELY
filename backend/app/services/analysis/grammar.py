# Define standard variations for each word to improve transcription matching
HARE_VARIANTS = ("hare", "re", "hurry", "harry", "हरे", "हौरे", "ह")
KRISHNA_VARIANTS = ("krishna", "krishn", "krsna", "कृष्णा", "कृष्ण", "कृष")
RAMA_VARIANTS = ("rama", "ram", "रामा", "राम")

CANONICAL_MANTRA_SLOTS = [
    HARE_VARIANTS,
    KRISHNA_VARIANTS,
    HARE_VARIANTS,
    KRISHNA_VARIANTS,
    KRISHNA_VARIANTS,
    KRISHNA_VARIANTS,
    HARE_VARIANTS,
    HARE_VARIANTS,
    HARE_VARIANTS,
    RAMA_VARIANTS,
    HARE_VARIANTS,
    RAMA_VARIANTS,
    RAMA_VARIANTS,
    RAMA_VARIANTS,
    HARE_VARIANTS,
    HARE_VARIANTS,
]

CANONICAL_MANTRA_TEXT = "hare krishna hare krishna krishna krishna hare hare hare rama hare rama rama rama hare hare"

INTERRUPTION_TOKENS = {
    "uh",
    "um",
    "hmm",
    "huh",
    "cough",
    "sneeze",
    "throat",
    "noise",
    "breath",
}
