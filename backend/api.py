from flask import Flask, jsonify
import sqlite3
import re
from collections import Counter
import datetime
from flask_cors import CORS  # <-- newly added

app = Flask(__name__)
CORS(app)
DB_PATH = "var/dashdb.sqlite3"  # Path to your SQLite database file


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ========== Utility functions for parsing and generating year-month strings ==========


def compute_year_month_by_offset(offset_months: int):
    """
    Given an offset in months (0~12), return (year, month) representing
    the date obtained by subtracting offset_months from the current month.
    
    Example: If today is Mar 2025,
      offset_months=0 => (2025, 3)    for March
      offset_months=1 => (2025, 2)    for February
      offset_months=7 => (2024, 8)
      offset_months=12 => (2024, 3)
    """
    now = datetime.date.today()  # e.g., 2025-03-07
    year = now.year
    month = now.month  # 3

    # Move backward offset_months
    target_month = month - offset_months
    while target_month <= 0:
        target_month += 12
        year -= 1

    return year, target_month


def get_year_month_str(year, month):
    """
    Return a string like '2025-03', for comparing with the DB column in 'YYYY-MM' format.
    """
    return f"{year:04d}-{month:02d}"

# ========== 1. GET /api/posts/recent ==========


@app.route("/api/posts/recent", methods=["GET"])
def get_recent_posts():
    """
    Returns the most recent 50 posts, including date, content, and label.
    """
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT id, date, content, label
        FROM records
        ORDER BY date DESC
        LIMIT 50
    """).fetchall()
    conn.close()

    result = []
    for row in rows:
        result.append({
            "id": row["id"],
            "date": row["date"],
            "content": row["content"],
            "label": row["label"]
        })

    return jsonify(result)

# ========== 2. GET /api/metrics ==========


@app.route("/api/metrics", methods=["GET"])
def get_metrics():
    """
    Returns total post count and the counts of positive, negative, and neutral posts.
    """
    conn = get_db_connection()
    row = conn.execute("""
        SELECT
            COUNT(*) as totalPosts,
            SUM(CASE WHEN label=2 THEN 1 ELSE 0 END) as positiveCount,
            SUM(CASE WHEN label=0 THEN 1 ELSE 0 END) as negativeCount,
            SUM(CASE WHEN label=1 THEN 1 ELSE 0 END) as neutralCount
        FROM records
    """).fetchone()
    conn.close()

    result = {
        "totalPosts": row["positiveCount"] + row["negativeCount"] + row["neutralCount"],
        "positiveCount": row["positiveCount"],
        "negativeCount": row["negativeCount"],
        "neutralCount": row["neutralCount"]
    }
    return jsonify(result)

# ========== 3. GET /api/sentiment/<which_month> ==========


@app.route("/api/sentiment/<int:which_month>", methods=["GET"])
def get_sentiment_by_month(which_month):
    """
    Returns sentiment stats for a specific month offset:
      - which_month=0 => current month
      - which_month=7 => 7 months ago
      - which_month=12 => 12 months ago
    Summarizes counts for positive, negative, and neutral posts.
    
    Implementation detail:
      - compute (year, month) using offset
      - match records.date to that year-month
    """
    if which_month < 0 or which_month > 12:
        return jsonify({"error": "Month offset must be between 0 and 12"}), 400

    # Compute target (year, month)
    year, month = compute_year_month_by_offset(which_month)
    ym_str = get_year_month_str(year, month)  # e.g. '2024-08'

    conn = get_db_connection()
    # Match records whose date has the prefix 'YYYY-MM'
    rows = conn.execute("""
        SELECT
            SUM(CASE WHEN label=2 THEN 1 ELSE 0 END) as positiveCount,
            SUM(CASE WHEN label=0 THEN 1 ELSE 0 END) as negativeCount,
            SUM(CASE WHEN label=1 THEN 1 ELSE 0 END) as neutralCount
        FROM records
        WHERE substr(date,1,7) = ?
    """, (ym_str, )).fetchone()
    conn.close()

    result = {
        "year": year,
        "month": month,
        "positive": rows["positiveCount"] if rows["positiveCount"] else 0,
        "negative": rows["negativeCount"] if rows["negativeCount"] else 0,
        "neutral": rows["neutralCount"] if rows["neutralCount"] else 0
    }
    return jsonify(result)

# ========== 4. GET /api/sentiment/keyword ==========


@app.route("/api/sentiment/keyword", methods=["GET"])
def get_keywords_by_sentiment():
    """
    Looks at the last 12 months of records, obtains the most frequent words
    (excluding stopwords) for each label=0,1,2. 
    Returns the top words for negative, neutral, and positive posts.
    """
    conn = get_db_connection()

    # Compute the range for the last 12 months (including current)
    # Example: if now is 2025-03 => 12 months ago => 2024-03
    # We'll gather [2024-03, 2025-03].
    now = datetime.date.today()
    now_ym = get_year_month_str(now.year, now.month)  # e.g. '2025-03'

    past_year, past_month = compute_year_month_by_offset(12)
    past_ym = get_year_month_str(past_year, past_month)  # e.g. '2024-03'

    rows = conn.execute("""
        SELECT content, label
        FROM records
        WHERE label IN (0,1,2)
        AND substr(date,1,7) >= ?
        AND substr(date,1,7) <= ?
    """, (past_ym, now_ym)).fetchall()
    conn.close()

    # Separate records by label
    texts_by_label = {0: [], 1: [], 2: []}
    for row in rows:
        lab = row["label"]
        txt = row["content"] or ""
        texts_by_label[lab].append(txt)

    # Example stopwords (expand as needed)
    stopwords = {
        "prevent", "address", "sanctions", "change", "events", "region", "warning", "issue", "programs", "response", "leader", "administration", "situation", "public", "discusses", "international", "officials", "strategy", "decision", "impact", "states", "united", "support", "focus", "test", "text", "nuclear", "0o", "0s", "3a", "3b", "3d", "6b", "6o", "a", "a1", "a2", "a3", "a4", "ab", "able", "about", "above", "abst", "ac", "accordance", "according", "accordingly", "across", "act", "actually", "ad", "added", "adj", "ae", "af", "affected", "affecting", "affects", "after", "afterwards", "ag", "again", "against", "ah", "ain", "ain't", "aj", "al", "all", "allow", "allows", "almost", "alone", "along", "already", "also", "although", "always", "am", "among", "amongst", "amoungst", "amount", "an", "and", "announce", "another", "any", "anybody", "anyhow", "anymore", "anyone", "anything", "anyway", "anyways", "anywhere", "ao", "ap", "apart", "apparently", "appear", "appreciate", "appropriate", "approximately", "ar", "are", "aren", "arent", "aren't", "arise", "around", "as", "a's", "aside", "ask", "asking", "associated", "at", "au", "auth", "av", "available", "aw", "away", "awfully", "ax", "ay", "az", "b", "b1", "b2", "b3", "ba", "back", "bc", "bd", "be", "became", "because", "become", "becomes", "becoming", "been", "before", "beforehand", "begin", "beginning", "beginnings", "begins", "behind", "being", "believe", "below", "beside", "besides", "best", "better", "between", "beyond", "bi", "bill", "biol", "bj", "bk", "bl", "bn", "both", "bottom", "bp", "br", "brief", "briefly", "bs", "bt", "bu", "but", "bx", "by", "c", "c1", "c2", "c3", "ca", "call", "came", "can", "cannot", "cant", "can't", "cause", "causes", "cc", "cd", "ce", "certain", "certainly", "cf", "cg", "ch", "changes", "ci", "cit", "cj", "cl", "clearly", "cm", "c'mon", "cn", "co", "com", "come", "comes", "con", "concerning", "consequently", "consider", "considering", "contain", "containing", "contains", "corresponding", "could", "couldn", "couldnt", "couldn't", "course", "cp", "cq", "cr", "cry", "cs", "c's", "ct", "cu", "currently", "cv", "cx", "cy", "cz", "d", "d2", "da", "date", "dc", "dd", "de", "definitely", "describe", "described", "despite", "detail", "df", "di", "did", "didn", "didn't", "different", "dj", "dk", "dl", "do", "does", "doesn", "doesn't", "doing", "don", "done", "don't", "down", "downwards", "dp", "dr", "ds", "dt", "du", "due", "during", "dx", "dy", "e", "e2", "e3", "ea", "each", "ec", "ed", "edu", "ee", "ef", "effect", "eg", "ei", "eight", "eighty", "either", "ej", "el", "eleven", "else", "elsewhere", "em", "empty", "en", "end", "ending", "enough", "entirely", "eo", "ep", "eq", "er", "es", "especially", "est", "et", "et-al", "etc", "eu", "ev", "even", "ever", "every", "everybody", "everyone", "everything", "everywhere", "ex", "exactly", "example", "except", "ey", "f", "f2", "fa", "far", "fc", "few", "ff", "fi", "fifteen", "fifth", "fify", "fill", "find", "fire", "first", "five", "fix", "fj", "fl", "fn", "fo", "followed", "following", "follows", "for", "former", "formerly", "forth", "forty", "found", "four", "fr", "from", "front", "fs", "ft", "fu", "full", "further", "furthermore", "fy", "g", "ga", "gave", "ge", "get", "gets", "getting", "gi", "give", "given", "gives", "giving", "gj", "gl", "go", "goes", "going", "gone", "got", "gotten", "gr", "greetings", "gs", "gy", "h", "h2", "h3", "had", "hadn", "hadn't", "happens", "hardly", "has", "hasn", "hasnt", "hasn't", "have", "haven", "haven't", "having", "he", "hed", "he'd", "he'll", "hello", "help", "hence", "her", "here", "hereafter", "hereby", "herein", "heres", "here's", "hereupon", "hers", "herself", "hes", "he's", "hh", "hi", "hid", "him", "himself", "his", "hither", "hj", "ho", "home", "hopefully", "how", "howbeit", "however", "how's", "hr", "hs", "http", "hu", "hundred", "hy", "i", "i2", "i3", "i4", "i6", "i7", "i8", "ia", "ib", "ibid", "ic", "id", "i'd", "ie", "if", "ig", "ignored", "ih", "ii", "ij", "il", "i'll", "im", "i'm", "immediate", "immediately", "importance", "important", "in", "inasmuch", "inc", "indeed", "index", "indicate", "indicated", "indicates", "information", "inner", "insofar", "instead", "interest", "into", "invention", "inward", "io", "ip", "iq", "ir", "is", "isn", "isn't", "it", "itd", "it'd", "it'll", "its", "it's", "itself", "iv", "i've", "ix", "iy", "iz", "j", "jj", "jr", "js", "jt", "ju", "just", "k", "ke", "keep", "keeps", "kept", "kg", "kj", "km", "know", "known", "knows", "ko", "l", "l2", "la", "largely", "last", "lately", "later", "latter", "latterly", "lb", "lc", "le", "least", "les", "less", "lest", "let", "lets", "let's", "lf", "like", "liked", "likely", "line", "little", "lj", "ll", "ll", "ln", "lo", "look", "looking", "looks", "los", "lr", "ls", "lt", "ltd", "m", "m2", "ma", "made", "mainly", "make", "makes", "many", "may", "maybe", "me", "mean", "means", "meantime", "meanwhile", "merely", "mg", "might", "mightn", "mightn't", "mill", "million", "mine", "miss", "ml", "mn", "mo", "more", "moreover", "most", "mostly", "move", "mr", "mrs", "ms", "mt", "mu", "much", "mug", "must", "mustn", "mustn't", "my", "myself", "n", "n2", "na", "name", "namely", "nay", "nc", "nd", "ne", "near", "nearly", "necessarily", "necessary", "need", "needn", "needn't", "needs", "neither", "never", "nevertheless", "new", "next", "ng", "ni", "nine", "ninety", "nj", "nl", "nn", "no", "nobody", "non", "none", "nonetheless", "noone", "nor", "normally", "nos", "not", "noted", "nothing", "novel", "now", "nowhere", "nr", "ns", "nt", "ny", "o", "oa", "ob", "obtain", "obtained", "obviously", "oc", "od", "of", "off", "often", "og", "oh", "oi", "oj", "ok", "okay", "ol", "old", "om", "omitted", "on", "once", "one", "ones", "only", "onto", "oo", "op", "oq", "or", "ord", "os", "ot", "other", "others", "otherwise", "ou", "ought", "our", "ours", "ourselves", "out", "outside", "over", "overall", "ow", "owing", "own", "ox", "oz", "p", "p1", "p2", "p3", "page", "pagecount", "pages", "par", "part", "particular", "particularly", "pas", "past", "pc", "pd", "pe", "per", "perhaps", "pf", "ph", "pi", "pj", "pk", "pl", "placed", "please", "plus", "pm", "pn", "po", "poorly", "possible", "possibly", "potentially", "pp", "pq", "pr", "predominantly", "present", "presumably", "previously", "primarily", "probably", "promptly", "proud", "provides", "ps", "pt", "pu", "put", "py", "q", "qj", "qu", "que", "quickly", "quite", "qv", "r", "r2", "ra", "ran", "rather", "rc", "rd", "re", "readily", "really", "reasonably", "recent", "recently", "ref", "refs", "regarding", "regardless", "regards", "related", "relatively", "research", "research-articl", "respectively", "resulted", "resulting", "results", "rf", "rh", "ri", "right", "rj", "rl", "rm", "rn", "ro", "rq", "rr", "rs", "rt", "ru", "run", "rv", "ry", "s", "s2", "sa", "said", "same", "saw", "say", "saying", "says", "sc", "sd", "se", "sec", "second", "secondly", "section", "see", "seeing", "seem", "seemed", "seeming", "seems", "seen", "self", "selves", "sensible", "sent", "serious", "seriously", "seven", "several", "sf", "shall", "shan", "shan't", "she", "shed", "she'd", "she'll", "shes", "she's", "should", "shouldn", "shouldn't", "should've", "show", "showed", "shown", "showns", "shows", "si", "side", "significant", "significantly", "similar", "similarly", "since", "sincere", "six", "sixty", "sj", "sl", "slightly", "sm", "sn", "so", "some", "somebody", "somehow", "someone", "somethan", "something", "sometime", "sometimes", "somewhat", "somewhere", "soon", "sorry", "sp", "specifically", "specified", "specify", "specifying", "sq", "sr", "ss", "st", "still", "stop", "strongly", "sub", "substantially", "successfully", "such", "sufficiently", "suggest", "sup", "sure", "sy", "system", "sz", "t", "t1", "t2", "t3", "take", "taken", "taking", "tb", "tc", "td", "te", "tell", "ten", "tends", "tf", "th", "than", "thank", "thanks", "thanx", "that", "that'll", "thats", "that's", "that've", "the", "their", "theirs", "them", "themselves", "then", "thence", "there", "thereafter", "thereby", "thered", "therefore", "therein", "there'll", "thereof", "therere", "theres", "there's", "thereto", "thereupon", "there've", "these", "they", "theyd", "they'd", "they'll", "theyre", "they're", "they've", "thickv", "thin", "think", "third", "this", "thorough", "thoroughly", "those", "thou", "though", "thoughh", "thousand", "three", "throug", "through", "throughout", "thru", "thus", "ti", "til", "tip", "tj", "tl", "tm", "tn", "to", "together", "too", "took", "top", "toward", "towards", "tp", "tq", "tr", "tried", "tries", "truly", "try", "trying", "ts", "t's", "tt", "tv", "twelve", "twenty", "twice", "two", "tx", "u", "u201d", "ue", "ui", "uj", "uk", "um", "un", "under", "unfortunately", "unless", "unlike", "unlikely", "until", "unto", "uo", "up", "upon", "ups", "ur", "us", "use", "used", "useful", "usefully", "usefulness", "uses", "using", "usually", "ut", "v", "va", "value", "various", "vd", "ve", "ve", "very", "via", "viz", "vj", "vo", "vol", "vols", "volumtype", "vq", "vs", "vt", "vu", "w", "wa", "want", "wants", "was", "wasn", "wasnt", "wasn't", "way", "we", "wed", "we'd", "welcome", "well", "we'll", "well-b", "went", "were", "we're", "weren", "werent", "weren't", "we've", "what", "whatever", "what'll", "whats", "what's", "when", "whence", "whenever", "when's", "where", "whereafter", "whereas", "whereby", "wherein", "wheres", "where's", "whereupon", "wherever", "whether", "which", "while", "whim", "whither", "who", "whod", "whoever", "whole", "who'll", "whom", "whomever", "whos", "who's", "whose", "why", "why's", "wi", "widely", "will", "willing", "wish", "with", "within", "without", "wo", "won", "wonder", "wont", "won't", "words", "world", "would", "wouldn", "wouldnt", "wouldn't", "www", "x", "x1", "x2", "x3", "xf", "xi", "xj", "xk", "xl", "xn", "xo", "xs", "xt", "xv", "xx", "y", "y2", "yes", "yet", "yj", "yl", "you", "youd", "you'd", "you'll", "your", "youre", "you're", "yours", "yourself", "yourselves", "you've", "yr", "ys", "yt", "z", "zero", "zi", "zz"
    }

    def tokenize(text):
        tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
        tokens = [t for t in tokens if len(t) >= 2 and t not in stopwords]
        return tokens

    top_words = {0: [], 1: [], 2: []}
    for lab in (0, 1, 2):
        big_text = " ".join(texts_by_label[lab])
        tokens = tokenize(big_text)
        freq = Counter(tokens)
        most_common_ = [word for word, _ in freq.most_common(100)]
        top_words[lab] = most_common_

    result = {
        "negative": top_words[0],
        "neutral":  top_words[1],
        "positive": top_words[2]
    }
    return jsonify(result)


# ========== Entry point ==========

if __name__ == "__main__":
    app.run(debug=True)
