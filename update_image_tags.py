#!/usr/bin/env python3
"""
update_image_tags.py

Refreshes the `tags` and `search_terms` fields on existing Firestore documents
in the `aac_images` collection to match the current tag-generation logic:

  • concept and subconcept stored as-is (lowercase)
  • subconcept also stored with underscores replaced by spaces
    ("not_now" → "not now") so either spelling finds the image
  • concept tokens (single-word categories only)
  • verb conjugations for single-word subconcepts
    (subconcept "tell" gets tags "telling", "told", "tells", …)
  • subconcept is NO LONGER split into individual words
    ("not_now" no longer adds "not" and "now" as standalone tags)

Usage (dry run — shows what would change, writes nothing):
    python3 update_image_tags.py --project bravo-test-465400

Write changes:
    python3 update_image_tags.py --project bravo-test-465400 --write

Filter to a specific mascot:
    python3 update_image_tags.py --project bravo-test-465400 --mascot bonnie --write

Filter to a specific concept (category):
    python3 update_image_tags.py --project bravo-test-465400 --concept feelings --write
"""

import argparse
import re
import sys
from typing import Optional

# ── verb conjugation table ─────────────────────────────────────────────────────
# Maps base (infinitive) → set of common inflected forms.
# Used to enrich tags so "telling" / "told" both find the "tell" image.
_BASE_TO_FORMS: dict[str, tuple[str, ...]] = {
    "be":         ("am", "is", "are", "was", "were", "been", "being"),
    "eat":        ("ate", "eaten", "eating", "eats"),
    "drink":      ("drank", "drunk", "drinking", "drinks"),
    "go":         ("went", "gone", "going", "goes"),
    "come":       ("came", "coming", "comes"),
    "run":        ("ran", "running", "runs"),
    "see":        ("saw", "seen", "seeing", "sees"),
    "say":        ("said", "saying", "says"),
    "tell":       ("told", "telling", "tells"),
    "speak":      ("spoke", "spoken", "speaking", "speaks"),
    "ask":        ("asked", "asking", "asks"),
    "look":       ("looked", "looking", "looks"),
    "watch":      ("watched", "watching", "watches"),
    "hear":       ("heard", "hearing", "hears"),
    "feel":       ("felt", "feeling", "feels"),
    "give":       ("gave", "given", "giving", "gives"),
    "take":       ("took", "taken", "taking", "takes"),
    "make":       ("made", "making", "makes"),
    "get":        ("got", "gotten", "getting", "gets"),
    "put":        ("putting", "puts"),
    "set":        ("setting", "sets"),
    "let":        ("letting", "lets"),
    "cut":        ("cutting", "cuts"),
    "hit":        ("hitting", "hits"),
    "hurt":       ("hurting", "hurts"),
    "read":       ("reading", "reads"),
    "know":       ("knew", "known", "knowing", "knows"),
    "think":      ("thought", "thinking", "thinks"),
    "mean":       ("meant", "meaning", "means"),
    "find":       ("found", "finding", "finds"),
    "lose":       ("lost", "losing", "loses"),
    "keep":       ("kept", "keeping", "keeps"),
    "leave":      ("left", "leaving", "leaves"),
    "bring":      ("brought", "bringing", "brings"),
    "buy":        ("bought", "buying", "buys"),
    "teach":      ("taught", "teaching", "teaches"),
    "think":      ("thought", "thinking", "thinks"),
    "catch":      ("caught", "catching", "catches"),
    "fall":       ("fell", "fallen", "falling", "falls"),
    "hold":       ("held", "holding", "holds"),
    "send":       ("sent", "sending", "sends"),
    "sit":        ("sat", "sitting", "sits"),
    "sleep":      ("slept", "sleeping", "sleeps"),
    "stand":      ("stood", "standing", "stands"),
    "wear":       ("wore", "worn", "wearing", "wears"),
    "win":        ("won", "winning", "wins"),
    "write":      ("wrote", "written", "writing", "writes"),
    "draw":       ("drew", "drawn", "drawing", "draws"),
    "sing":       ("sang", "sung", "singing", "sings"),
    "swim":       ("swam", "swum", "swimming", "swims"),
    "throw":      ("threw", "thrown", "throwing", "throws"),
    "fly":        ("flew", "flown", "flying", "flies"),
    "ride":       ("rode", "ridden", "riding", "rides"),
    "drive":      ("drove", "driven", "driving", "drives"),
    "fall":       ("fell", "fallen", "falling", "falls"),
    "meet":       ("met", "meeting", "meets"),
    "pay":        ("paid", "paying", "pays"),
    "lead":       ("led", "leading", "leads"),
    "feed":       ("fed", "feeding", "feeds"),
    "build":      ("built", "building", "builds"),
    "fight":      ("fought", "fighting", "fights"),
    "show":       ("showed", "shown", "showing", "shows"),
    "spend":      ("spent", "spending", "spends"),
    "wake":       ("woke", "woken", "waking", "wakes"),
    "break":      ("broke", "broken", "breaking", "breaks"),
    "choose":     ("chose", "chosen", "choosing", "chooses"),
    "grow":       ("grew", "grown", "growing", "grows"),
    "blow":       ("blew", "blown", "blowing", "blows"),
    "begin":      ("began", "begun", "beginning", "begins"),
    "ring":       ("rang", "rung", "ringing", "rings"),
    "forget":     ("forgot", "forgotten", "forgetting", "forgets"),
    "freeze":     ("froze", "frozen", "freezing", "freezes"),
    "bite":       ("bit", "bitten", "biting", "bites"),
    "hide":       ("hid", "hidden", "hiding", "hides"),
    "shake":      ("shook", "shaken", "shaking", "shakes"),
    "steal":      ("stole", "stolen", "stealing", "steals"),
    "swing":      ("swung", "swinging", "swings"),
    "stick":      ("stuck", "sticking", "sticks"),
    "dig":        ("dug", "digging", "digs"),
    "slide":      ("slid", "sliding", "slides"),
    "spin":       ("spun", "spinning", "spins"),
    "tear":       ("tore", "torn", "tearing", "tears"),
    "understand": ("understood", "understanding", "understands"),
    "bend":       ("bent", "bending", "bends"),
    "bleed":      ("bled", "bleeding", "bleeds"),
    "light":      ("lit", "lighting", "lights"),
    "lay":        ("laid", "laying", "lays"),
    "rise":       ("rose", "risen", "rising", "rises"),
    "weep":       ("wept", "weeping", "weeps"),
    "sweep":      ("swept", "sweeping", "sweeps"),
    "swear":      ("swore", "sworn", "swearing", "swears"),
    "spread":     ("spreading", "spreads"),
    "burst":      ("bursting", "bursts"),
    "cost":       ("costing", "costs"),
    "shut":       ("shutting", "shuts"),
    # regular verbs commonly used as AAC image labels
    "play":       ("played", "playing", "plays"),
    "walk":       ("walked", "walking", "walks"),
    "talk":       ("talked", "talking", "talks"),
    "jump":       ("jumped", "jumping", "jumps"),
    "laugh":      ("laughed", "laughing", "laughs"),
    "cry":        ("cried", "crying", "cries"),
    "try":        ("tried", "trying", "tries"),
    "help":       ("helped", "helping", "helps"),
    "want":       ("wanted", "wanting", "wants"),
    "need":       ("needed", "needing", "needs"),
    "like":       ("liked", "liking", "likes"),
    "love":       ("loved", "loving", "loves"),
    "hate":       ("hated", "hating", "hates"),
    "hug":        ("hugged", "hugging", "hugs"),
    "kiss":       ("kissed", "kissing", "kisses"),
    "smile":      ("smiled", "smiling", "smiles"),
    "wave":       ("waved", "waving", "waves"),
    "dance":      ("danced", "dancing", "dances"),
    "paint":      ("painted", "painting", "paints"),
    "color":      ("colored", "coloring", "colors"),
    "open":       ("opened", "opening", "opens"),
    "close":      ("closed", "closing", "closes"),
    "stop":       ("stopped", "stopping", "stops"),
    "start":      ("started", "starting", "starts"),
    "finish":     ("finished", "finishing", "finishes"),
    "clean":      ("cleaned", "cleaning", "cleans"),
    "cook":       ("cooked", "cooking", "cooks"),
    "push":       ("pushed", "pushing", "pushes"),
    "pull":       ("pulled", "pulling", "pulls"),
    "work":       ("worked", "working", "works"),
    "wait":       ("waited", "waiting", "waits"),
    "share":      ("shared", "sharing", "shares"),
    "turn":       ("turned", "turning", "turns"),
    "move":       ("moved", "moving", "moves"),
    "kick":       ("kicked", "kicking", "kicks"),
    "climb":      ("climbed", "climbing", "climbs"),
    "call":       ("called", "calling", "calls"),
    "visit":      ("visited", "visiting", "visits"),
    "learn":      ("learned", "learning", "learns"),
    "listen":     ("listened", "listening", "listens"),
    "touch":      ("touched", "touching", "touches"),
    "point":      ("pointed", "pointing", "points"),
    "change":     ("changed", "changing", "changes"),
    "use":        ("used", "using", "uses"),
    "pick":       ("picked", "picking", "picks"),
    "draw":       ("drew", "drawn", "drawing", "draws"),
    "pour":       ("poured", "pouring", "pours"),
    "mix":        ("mixed", "mixing", "mixes"),
    "bake":       ("baked", "baking", "bakes"),
    "print":      ("printed", "printing", "prints"),
    "type":       ("typed", "typing", "types"),
    "text":       ("texted", "texting", "texts"),
    "answer":     ("answered", "answering", "answers"),
    "pass":       ("passed", "passing", "passes"),
    "count":      ("counted", "counting", "counts"),
    "add":        ("added", "adding", "adds"),
    "hike":       ("hiked", "hiking", "hikes"),
    "camp":       ("camped", "camping", "camps"),
    "fish":       ("fished", "fishing", "fishes"),
    "rest":       ("rested", "resting", "rests"),
    "shower":     ("showered", "showering", "showers"),
    "brush":      ("brushed", "brushing", "brushes"),
    "dress":      ("dressed", "dressing", "dresses"),
    "spell":      ("spelled", "spelling", "spells"),
    "practice":   ("practiced", "practicing", "practices"),
    "exercise":   ("exercised", "exercising", "exercises"),
    "jog":        ("jogged", "jogging", "jogs"),
    "hop":        ("hopped", "hopping", "hops"),
    "skip":       ("skipped", "skipping", "skips"),
    "bounce":     ("bounced", "bouncing", "bounces"),
    "stomp":      ("stomped", "stomping", "stomps"),
    "clap":       ("clapped", "clapping", "claps"),
    "snap":       ("snapped", "snapping", "snaps"),
    "tap":        ("tapped", "tapping", "taps"),
    "pat":        ("patted", "patting", "pats"),
    "rub":        ("rubbed", "rubbing", "rubs"),
    "scratch":    ("scratched", "scratching", "scratches"),
    "squeeze":    ("squeezed", "squeezing", "squeezes"),
    "grab":       ("grabbed", "grabbing", "grabs"),
    "carry":      ("carried", "carrying", "carries"),
    "lift":       ("lifted", "lifting", "lifts"),
    "drop":       ("dropped", "dropping", "drops"),
    "whisper":    ("whispered", "whispering", "whispers"),
    "shout":      ("shouted", "shouting", "shouts"),
    "yell":       ("yelled", "yelling", "yells"),
    "scream":     ("screamed", "screaming", "screams"),
    "hum":        ("hummed", "humming", "hums"),
    "remember":   ("remembered", "remembering", "remembers"),
    "forget":     ("forgot", "forgotten", "forgetting", "forgets"),
    "wonder":     ("wondered", "wondering", "wonders"),
    "imagine":    ("imagined", "imagining", "imagines"),
    "pretend":    ("pretended", "pretending", "pretends"),
    "hope":       ("hoped", "hoping", "hopes"),
    "wish":       ("wished", "wishing", "wishes"),
    "dream":      ("dreamed", "dreaming", "dreams"),
    "worry":      ("worried", "worrying", "worries"),
    "care":       ("cared", "caring", "cares"),
    "celebrate":  ("celebrated", "celebrating", "celebrates"),
    "follow":     ("followed", "following", "follows"),
    "create":     ("created", "creating", "creates"),
    "save":       ("saved", "saving", "saves"),
    "fix":        ("fixed", "fixing", "fixes"),
    "check":      ("checked", "checking", "checks"),
    "connect":    ("connected", "connecting", "connects"),
    "decide":     ("decided", "deciding", "decides"),
    "explain":    ("explained", "explaining", "explains"),
    "describe":   ("described", "describing", "describes"),
    "happen":     ("happened", "happening", "happens"),
    "allow":      ("allowed", "allowing", "allows"),
    "stay":       ("stayed", "staying", "stays"),
    "return":     ("returned", "returning", "returns"),
    "prepare":    ("prepared", "preparing", "prepares"),
    "collect":    ("collected", "collecting", "collects"),
    "repeat":     ("repeated", "repeating", "repeats"),
    "relax":      ("relaxed", "relaxing", "relaxes"),
    "choose":     ("chose", "chosen", "choosing", "chooses"),
    "connect":    ("connected", "connecting", "connects"),
}

# Build the reverse map: inflected → base (used to avoid adding duplicate base)
_FORM_TO_BASE: dict[str, str] = {}
for _base, _forms in _BASE_TO_FORMS.items():
    for _form in _forms:
        _FORM_TO_BASE[_form] = _base


_MASCOT_TOKENS = {"bobby", "bonnie", "buddy", "mascot", "no"}


def _tokenize(text: str) -> list[str]:
    """Split on whitespace and underscores (for concept/category names only).
    Excludes mascot-related tokens so they are never added to searchable tags."""
    return [t for t in re.split(r"[\s_]+", text.lower()) if t and t not in _MASCOT_TOKENS]


def _verb_forms_for(word: str) -> set[str]:
    """
    Return all known conjugated forms of word if it is a recognised verb base.
    Returns an empty set for unknown words or inflected forms.
    """
    w = word.lower().strip()
    if w in _BASE_TO_FORMS:
        return set(_BASE_TO_FORMS[w])
    return set()


# ── noun pluralization ─────────────────────────────────────────────────────────

_NOUN_IRREGULARS: dict[str, str] = {
    "person":    "people",
    "child":     "children",
    "man":       "men",
    "woman":     "women",
    "tooth":     "teeth",
    "foot":      "feet",
    "goose":     "geese",
    "mouse":     "mice",
    "ox":        "oxen",
    "leaf":      "leaves",
    "knife":     "knives",
    "life":      "lives",
    "wife":      "wives",
    "wolf":      "wolves",
    "shelf":     "shelves",
    "self":      "selves",
    "half":      "halves",
    "loaf":      "loaves",
    "scarf":     "scarves",
    "calf":      "calves",
    "elf":       "elves",
    "thief":     "thieves",
    "potato":    "potatoes",
    "tomato":    "tomatoes",
    "hero":      "heroes",
    "echo":      "echoes",
    "photo":     "photos",
    "piano":     "pianos",
    "radio":     "radios",
    "video":     "videos",
    "zoo":       "zoos",
}

_NOUNS_INVARIANT: frozenset = frozenset({
    "fish", "sheep", "deer", "moose", "bison", "swine",
    "aircraft", "series", "species", "offspring",
    "water", "milk", "juice", "food", "bread", "rice", "pasta",
    "soup", "air", "music", "hair", "money", "homework", "fun",
    "sand", "snow", "rain", "sunshine", "darkness", "silence",
})

# Map from expanded auxiliary forms to their _norm-equivalent contracted forms.
# Apostrophes become spaces under _norm, so "that's" → "that s", "you're" → "you re".
# Used to add contracted tags to images stored with expanded subconcepts.
_AUXILIARY_TO_CONTRACTION: dict[str, str] = {
    "is":    "s",
    "are":   "re",
    "am":    "m",
    "will":  "ll",
    "have":  "ve",
    "has":   "s",
    "had":   "d",
    "would": "d",
}

# Map from no-apostrophe contraction spellings to their _norm-equivalent spaced form.
# Used to add spaced tags to images uploaded from folder names without apostrophes.
_CONTRACTION_EXPAND: dict[str, str] = {
    "wont":    "won t",
    "cant":    "can t",
    "dont":    "don t",
    "shouldnt": "shouldn t",
    "wouldnt": "wouldn t",
    "couldnt": "couldn t",
    "mustnt":  "mustn t",
    "isnt":    "isn t",
    "arent":   "aren t",
    "wasnt":   "wasn t",
    "werent":  "weren t",
    "hasnt":   "hasn t",
    "havent":  "haven t",
    "hadnt":   "hadn t",
    "didnt":   "didn t",
    "doesnt":  "doesn t",
    "neednt":  "needn t",
    "shant":   "shan t",
}


def _contracted_forms(phrase: str) -> list[str]:
    """Return normalized contracted variants for a phrase with expandable auxiliaries.

    Each contractable auxiliary word is independently replaced to generate one
    variant per auxiliary found.  Examples:
      "that is wrong"   → ["that s wrong"]
      "you are right"   → ["you re right"]
      "i will be there" → ["i ll be there"]
    """
    words = phrase.split()
    forms = []
    for i, w in enumerate(words):
        if w in _AUXILIARY_TO_CONTRACTION:
            new_words = words[:i] + [_AUXILIARY_TO_CONTRACTION[w]] + words[i + 1:]
            forms.append(" ".join(new_words))
    return forms


def _is_noun_wordnet(word: str) -> bool | None:
    """
    Use WordNet to decide if a word is primarily a noun.
    Returns True/False when WordNet is available, None when it is not.

    Logic: noun synset count must be non-zero AND greater than verb synset count.
    This correctly rejects adjectives (0 noun synsets), pure verbs (0 noun synsets),
    and verb-dominant words like "jog" (more verb than noun synsets).
    Install: pip install nltk && python -m nltk.downloader wordnet omw-1.4
    """
    try:
        from nltk.corpus import wordnet as wn
        noun_count = len(wn.synsets(word, pos=wn.NOUN))
        verb_count = len(wn.synsets(word, pos=wn.VERB))
        if noun_count == 0:
            return False
        return noun_count > verb_count
    except LookupError:
        return None
    except ImportError:
        return None


def _is_noun_heuristic(word: str) -> bool:
    """Conservative suffix-based fallback used when WordNet is unavailable."""
    w = word.lower()
    if w in _BASE_TO_FORMS:
        return False
    if w.endswith('ing'):
        return False
    if w.endswith('ed'):
        return False
    if w.endswith(('ful', 'less', 'ous', 'ive', 'ible', 'able',
                   'ary', 'ory', 'ly', 'ent', 'ant',
                   'ward', 'ish', 'some')):
        return False
    return True


def _is_noun(word: str) -> bool:
    result = _is_noun_wordnet(word)
    if result is not None:
        return result
    return _is_noun_heuristic(word)


def _apply_plural_rules(w: str) -> str:
    if w in _NOUN_IRREGULARS:
        return _NOUN_IRREGULARS[w]
    if w.endswith(('ss', 'sh', 'ch', 'x', 'zz')):
        return w + 'es'
    if w.endswith('z') and not w.endswith('zz'):
        return w + 'zes'
    if w.endswith('s') and not w.endswith('ss'):
        return ''
    vowels = set('aeiou')
    if w.endswith('y') and len(w) > 1 and w[-2] not in vowels:
        return w[:-1] + 'ies'
    if w.endswith('fe'):
        return w[:-2] + 'ves'
    if w.endswith('f') and len(w) > 2:
        return w[:-1] + 'ves'
    return w + 's'


def _noun_plural(word: str) -> str:
    """
    Return the plural of a singular noun, or '' if the word is not a noun,
    is invariant/uncountable, or is already plural.

    Uses WordNet (NLTK) for part-of-speech detection when available.
    Install: pip install nltk && python -m nltk.downloader wordnet omw-1.4
    Falls back to suffix heuristics if NLTK is not installed.
    """
    w = word.lower().strip()
    if not w or w in _NOUNS_INVARIANT:
        return ''
    if w in _BASE_TO_FORMS:
        return ''
    if not _is_noun(w):
        return ''
    return _apply_plural_rules(w)


def compute_tags(concept: str, subconcept: str) -> list[str]:
    """
    Recompute tags for a document using the current tag-generation rules.

    Rules (matching process_and_upload_images.py):
      1. concept (lowercase)
      2. subconcept (lowercase, with underscores preserved)
      3. subconcept with underscores replaced by spaces
      4. tokens of concept (single-word categories — safe to split)
      5. verb conjugations for single-word subconcepts
      6. noun plural for single-word subconcepts

    NOT applied:
      • subconcept is never split into individual word tokens
        ("not_now" does NOT add "not" or "now" as separate tags)
    """
    sub_lower = subconcept.lower()
    sub_spaced = sub_lower.replace("_", " ")
    # Normalized form matching server._norm(): all non-alphanumeric → space.
    # Ensures "t-rex" image is found when option text "t-rex" normalizes to "t rex".
    sub_norm = " ".join(re.sub(r"[^a-z0-9]+", " ", sub_spaced).split())

    concept_lower = concept.lower()
    concept_tokens = {t for t in re.split(r"[\s_]+", concept_lower) if t}
    concept_is_mascot_label = bool(concept_tokens) and concept_tokens.issubset(_MASCOT_TOKENS)

    tag_set: set[str] = {
        sub_lower,
        sub_spaced,
        sub_norm,
        *_tokenize(concept),
    }
    if not concept_is_mascot_label:
        tag_set.add(concept_lower)

    if " " not in sub_spaced:
        tag_set.update(_verb_forms_for(sub_spaced))
        # Use suffix heuristic (not WordNet) for plural gating — WordNet was too aggressive,
        # excluding real nouns like "foster", "visual", "firm". The heuristic filters
        # clear non-nouns (-ing, -ed, -ward, -ish, -ful, -less, etc.) without over-excluding.
        if sub_spaced not in _NOUNS_INVARIANT and _is_noun_heuristic(sub_spaced):
            plural = _apply_plural_rules(sub_spaced)
            if plural and plural != sub_spaced:
                tag_set.add(plural)
    else:
        # For multi-word subconcepts, pluralize the last word (head noun).
        # "next step"→"next steps", "good morning"→"good mornings", "throughout the land"→"throughout the lands"
        # Skip the verb/adjective heuristic here — in phrase-final position the word is
        # almost always a noun (e.g. "morning" ends in -ing but is a noun, not a gerund).
        _words = sub_spaced.split()
        _last = _words[-1]
        if _last not in _NOUNS_INVARIANT:
            _plural_last = _apply_plural_rules(_last)
            if _plural_last and _plural_last != _last:
                tag_set.add(" ".join(_words[:-1] + [_plural_last]))

    # For subconcepts containing apostrophes (e.g. "ma'am", "don't want"), also add
    # the normalized form with apostrophes replaced by spaces so the server's _norm-based
    # lookup ("ma am", "don t want") finds this image.
    if "'" in sub_spaced or "’" in sub_spaced:
        spaced = re.sub(r"['‘’]", " ", sub_spaced)
        spaced_norm = " ".join(re.sub(r"[^a-z0-9]+", " ", spaced).split())
        if spaced_norm and spaced_norm != sub_spaced:
            tag_set.add(spaced_norm)

    # For subconcepts uploaded without apostrophes (e.g. folder "i_wont" → subconcept "i wont"),
    # add the spaced contraction form that server._norm() produces from the apostrophe version.
    words = sub_spaced.split()
    expanded = [_CONTRACTION_EXPAND.get(w, w) for w in words]
    if expanded != words:
        tag_set.add(" ".join(expanded))

    # For subconcepts with expanded auxiliaries (e.g. "you are wrong"), add contracted
    # normalized forms ("you re wrong") so options using contractions ("you're wrong") match.
    for form in _contracted_forms(sub_spaced):
        tag_set.add(form)

    return sorted(tag_set)


# ── Firestore helpers ──────────────────────────────────────────────────────────

def get_db(project_id: str):
    import firebase_admin
    from firebase_admin import firestore
    if not firebase_admin._apps:
        firebase_admin.initialize_app(options={"projectId": project_id})
    return firestore.client()


def stream_documents(db, mascot: Optional[str], concept: Optional[str], source: str):
    """Stream aac_images documents, optionally filtered."""
    col = db.collection("aac_images")
    query = col.where("source", "==", source)
    if mascot:
        query = query.where("mascot", "==", mascot)
    if concept:
        query = query.where("concept", "==", concept)
    return query.stream()


# ── main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Update tags/search_terms on existing aac_images Firestore docs."
    )
    parser.add_argument("--project", default="bravo-test-465400",
                        help="GCP project ID (default: bravo-test-465400)")
    parser.add_argument("--write", action="store_true",
                        help="Write changes to Firestore (default: dry run)")
    parser.add_argument("--mascot", default=None,
                        help="Limit to a specific mascot (e.g. bonnie)")
    parser.add_argument("--concept", default=None,
                        help="Limit to a specific concept/category (e.g. feelings)")
    parser.add_argument("--source", default="bravo_images",
                        help="Document source filter (default: bravo_images)")
    parser.add_argument("--show-unchanged", action="store_true",
                        help="Also print docs whose tags are already correct")
    args = parser.parse_args()

    mode = "WRITE" if args.write else "DRY RUN"
    print(f"=== update_image_tags  [{mode}] ===")
    print(f"Project : {args.project}")
    print(f"Source  : {args.source}")
    print(f"Mascot  : {args.mascot or '(all)'}")
    print(f"Concept : {args.concept or '(all)'}")
    print()

    db = get_db(args.project)
    docs = list(stream_documents(db, args.mascot, args.concept, args.source))
    print(f"Found {len(docs)} document(s) to evaluate.\n")

    changed = 0
    unchanged = 0
    errors = 0

    for doc in docs:
        data = doc.to_dict()
        concept   = str(data.get("concept",   "") or "")
        subconcept = str(data.get("subconcept", "") or "")

        if not concept or not subconcept:
            print(f"  [SKIP] {doc.id} — missing concept or subconcept")
            errors += 1
            continue

        old_tags = sorted(set(data.get("tags", []) or []))
        new_tags = compute_tags(concept, subconcept)

        # Merge computed tags into existing ones — never remove manually-added tags
        # (e.g. "bye I'll call you" added via add_bye_tags.py).
        merged_tags = sorted(set(old_tags) | set(new_tags))
        added = sorted(set(new_tags) - set(old_tags))

        label = f"concept={concept!r}  sub={subconcept!r}  mascot={data.get('mascot') or '(none)'!r}"

        if not added:
            unchanged += 1
            if args.show_unchanged:
                print(f"  [OK]   {doc.id}  {label}")
            continue

        changed += 1
        print(f"  [DIFF] {doc.id}  {label}")
        print(f"         + {added}")

        if args.write:
            try:
                doc.reference.update({
                    "tags":         merged_tags,
                    "search_terms": merged_tags,
                })
                print(f"         ✓ updated")
            except Exception as exc:
                print(f"         ✗ ERROR: {exc}", file=sys.stderr)
                errors += 1

    print()
    print(f"Summary: {changed} tags added, {unchanged} unchanged, {errors} errors")
    if not args.write and changed:
        print("Run with --write to apply changes.")
    print("Note: existing manually-added tags are always preserved (never removed).")


if __name__ == "__main__":
    main()
