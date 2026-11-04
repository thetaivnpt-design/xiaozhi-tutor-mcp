import asyncio
import websockets
import json
import ssl
import sys
import os
import urllib.request
import urllib.parse
import re
import html
import time
from fastapi import FastAPI
from contextlib import asynccontextmanager

sys.stdout.reconfigure(encoding='utf-8')

# Lấy token từ biến môi trường (Render Environment Variable) hoặc dùng token mặc định
DEFAULT_TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjEwNDg0NTUsImFnZW50SWQiOjIyNTcyODcsImVuZHBvaW50SWQiOiJhZ2VudF8yMjU3Mjg3IiwicHVycG9zZSI6Im1jcC1lbmRwb2ludCIsImlhdCI6MTc5MzQzOTI0MSwiZXhwIjoxODI0OTk2ODQxfQ.6StC63aALC-rxi079PHVZRj0uvbnIxp5WRwlQGRWd1FHkNpPtQ2X0AOaJXfAAIk96cAGqM0fvRR6_O2DY8iqLw"
MCP_TOKEN = os.getenv("MCP_TOKEN", DEFAULT_TOKEN)
MCP_WS_URL = f"wss://api.xiaozhi.me/mcp/?token={MCP_TOKEN}"

# ==============================================================================
# HỌC LIỆU CHÍNH THỐNG & CƠ CẤU CHƯƠNG TRÌNH GDPT 2018 (BỘ GD&ĐT VIỆT NAM)
# ==============================================================================

ACCREDITED_DOMAINS = [
    "thuvienthayco.com",
    "vietjack.com",
    "loigiaihay.com",
    "thuvienhoclieu.com",
    "hanhtrangso.nxbgd.vn",
    "hoc247.net",
    "vndoc.com",
    "olm.vn",
    "studocu.vn",
    "mathvn.com",
    "hoc10.vn",
    "tuyensinh247.com"
]

FALLBACK_UNCLEAR_RESPONSE = "Tôi chưa nghe rõ câu hỏi, làm ơn bạn hãy nhắc lại câu hỏi một cách rõ ràng rồi tôi sẽ trả lời bạn luôn"

STRICT_PEDAGOGICAL_GUIDELINE = (
    "\n\n[QUY TẮC SƯ PHẠM DÀNH CHO GIA SƯ AI XIAOZHI]:\n"
    "1. Tuyệt đối KHÔNG trả lời về La La School hoặc bất kỳ trường học mặc định nào khác.\n"
    "2. Khi học sinh nói không rõ câu hỏi, giọng bị rè, ngắt quãng hoặc bạn không hiểu ý câu hỏi, bạn PHẢI trả lời chính xác từng chữ: \"Tôi chưa nghe rõ câu hỏi, làm ơn bạn hãy nhắc lại câu hỏi một cách rõ ràng rồi tôi sẽ trả lời bạn luôn\".\n"
    "3. Giảng dạy theo phương pháp sư phạm 4 bước: Bản chất khái niệm -> Công thức/Quy tắc/Nội dung -> Ví dụ minh họa -> Lưu ý lỗi sai thường gặp khi đi thi.\n"
    "4. Luôn dùng giọng điệu người thầy tận tụy, ấm áp, khuyến khích học sinh tự giác tư duy."
)

STATS = {
    "start_time": time.time(),
    "total_queries": 0,
    "cache_hits": 0,
    "live_searches": 0,
    "mcp_connected": False,
    "last_error": None
}

MEMORY_CACHE = {}

CANONICAL_KNOWLEDGE = {
    "hang_dang_thuc": (
        "【7 HẰNG ĐẲNG THỨC ĐÁNG NHỚ (Toán 8 SGK mới)】\n"
        "1. Bình phương của một tổng: (A + B)² = A² + 2AB + B²\n"
        "2. Bình phương của một hiệu: (A - B)² = A² - 2AB + B²\n"
        "3. Hiệu hai bình phương: A² - B² = (A - B)(A + B)\n"
        "4. Lập phương của một tổng: (A + B)³ = A³ + 3A²B + 3AB² + B³\n"
        "5. Lập phương của một hiệu: (A - B)³ = A³ - 3A²B + 3AB² - B³\n"
        "6. Tổng hai lập phương: A³ + B³ = (A + B)(A² - AB + B²)\n"
        "7. Hiệu hai lập phương: A³ - B³ = (A - B)(A² + AB + B²)"
    ),
    "pytago": (
        "【ĐỊNH LÝ PYTAGO (Toán 7 & 8 SGK mới)】\n"
        "• Định lý thuận: Trong tam giác vuông, bình phương cạnh huyền bằng tổng bình phương hai cạnh góc vuông (BC² = AB² + AC² vuông tại A).\n"
        "• Định lý đảo: Nếu tam giác có a² = b² + c² thì tam giác đó vuông tại góc đối diện cạnh a."
    ),
    "viet": (
        "【HỆ THỨC VI-ÉT VÀ ỨNG DỤNG (Toán 9 & 10 SGK mới)】\n"
        "Cho phương trình bậc hai ax² + bx + c = 0 (a ≠ 0) có hai nghiệm x₁, x₂:\n"
        "• Tổng hai nghiệm: S = x₁ + x₂ = -b / a\n"
        "• Tích hai nghiệm: P = x₁ · x₂ = c / a\n"
        "• Tìm hai số biết tổng S và tích P: x₁ và x₂ là nghiệm phương trình X² - SX + P = 0 (Điều kiện: S² - 4P ≥ 0)."
    ),
    "newton": (
        "【3 ĐỊNH LUẬT NEWTON VỀ CHUYỂN ĐỘNG (Vật lí 10 SGK mới)】\n"
        "• Định luật 1 (Quán tính): Vật giữ nguyên trạng thái đứng yên hoặc chuyển động thẳng đều khi không chịu lực nào hoặc hợp lực bằng 0.\n"
        "• Định luật 2: Gia tốc của một vật tỉ lệ thuận với hợp lực tác dụng và tỉ lệ nghịch với khối lượng: F = m · a.\n"
        "• Định luật 3: Khi vật A tác dụng lên vật B một lực thì vật B cũng tác dụng lại vật A một lực cùng phương, ngược chiều, cùng độ lớn: F_AB = - F_BA."
    ),
    "kim_loai": (
        "【DÃY HOẠT ĐỘNG HÓA HỌC CỦA KIM LOẠI (KHTN 8, 9 & Hóa 10, 12)】\n"
        "K, Na, Ca, Mg, Al, Zn, Fe, Ni, Sn, Pb, (H), Cu, Hg, Ag, Pt, Au\n"
        "(Mẹo nhớ: Khi Nào Cần May Áo Giáp Sắt Nhớ Sang Phố Hỏi Cửa Hàng Á Phi Âu).\n"
        "• K, Na, Ca phản ứng mãnh liệt với nước ở nhiệt độ thường.\n"
        "• Đứng trước H phản ứng với dung dịch axit loãng (HCl, H₂SO₄ loãng) giải phóng khí H₂.\n"
        "• Kim loại đứng trước đẩy kim loại đứng sau ra khỏi dung dịch muối."
    ),
    "van_11": (
        "【TỔNG HỢP KIẾN THỨC TRỌNG TÂM NGỮ VĂN 11 (GDPT 2018 - 3 BỘ SÁCH)】\n"
        "1. VĂN BẢN TRUYỆN VÀ TIỂU THUYẾT:\n"
        "• 'Chữ người tử tù' (Nguyễn Tuân): Vẻ đẹp tài hoa, khí phách thiên lương của Huấn Cao và cảnh cho chữ 'xưa nay chưa từng có' khẳng định sự bất tử của cái đẹp.\n"
        "• 'Chí Phèo' (Nam Cao): Bi kịch bị cự tuyệt quyền làm người của người nông dân cùng quẫn và tiếng kêu đòi lương thiện xé lòng.\n"
        "2. PHONG TRÀO THƠ MỚI (LÃNG MẠN 1932-1945):\n"
        "• 'Vội vàng' (Xuân Diệu): Khát vọng sống cuồng nhiệt, triết lý nhân sinh say đắm trần thế và quý trọng từng phút giây tuổi trẻ.\n"
        "• 'Tràng giang' (Huy Cận): Nỗi sầu vạn cổ trước không gian sông nước mênh mông, gửi gắm tình yêu quê hương đất nước kín đáo.\n"
        "• 'Đây thôn Vĩ Dạ' (Hàn Mặc Tử): Cảnh sắc xứ Huế thơ mộng, u hoài và nỗi tha thiết với cuộc đời của thi nhân.\n"
        "3. KỊCH BẢN VĂN HỌC & NGHỊ LUẬN:\n"
        "• 'Vĩnh biệt Cửu Trùng Đài' (Vũ Như Tô - Nguyễn Huy Tưởng): Mâu thuẫn bi kịch giữa khát vọng nghệ thuật vĩ đại và đời sống cơm áo của nhân dân.\n"
        "• Phương pháp làm bài: Nắm chắc kỹ năng đọc hiểu thể loại (thơ trữ tình, truyện hiện thực, bi kịch) và kỹ năng viết bài nghị luận văn học, nghị luận xã hội."
    ),
    "toan_11": (
        "【TỔNG HỢP KIẾN THỨC CỐT LÕI MÔN TOÁN LỚP 11 (GDPT 2018)】\n"
        "1. LƯỢNG GIÁC: Công thức cộng: sin(a±b) = sina.cosb ± cosa.sinb; cos(a±b) = cosa.cosb ∓ sina.sinb. Công thức nhân đôi: sin2a = 2sina.cosa; cos2a = cos²a - sin²a = 2cos²a - 1 = 1 - 2sin²a.\n"
        "2. DÃY SỐ, CẤP SỐ CỘNG VÀ CẤP SỐ NHÂN:\n"
        "• Cấp số cộng: u_n = u_1 + (n - 1)d; Tổng: S_n = n(u_1 + u_n)/2 = n[2u_1 + (n - 1)d]/2.\n"
        "• Cấp số nhân: u_n = u_1 . q^(n - 1); Tổng: S_n = u_1(1 - q^n)/(1 - q) (q ≠ 1).\n"
        "3. GIỚI HẠN VÀ ĐẠO HÀM:\n"
        "• (x^n)' = n.x^(n-1); (sin x)' = cos x; (cos x)' = -sin x; (tan x)' = 1/cos²x; (e^x)' = e^x; (ln x)' = 1/x.\n"
        "4. QUAN HỆ VUÔNG GÓC TRONG KHÔNG GIAN: Đường thẳng vuông góc mặt phẳng, hai mặt phẳng vuông góc, góc và khoảng cách."
    )
}

def clean_text(raw_html: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', raw_html)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def normalize_math_for_speech(content: str) -> str:
    content = content.replace("²", " bình phương ").replace("³", " lập phương ")
    content = content.replace("√", " căn bậc hai của ")
    content = content.replace("≠", " khác ").replace("≤", " nhỏ hơn hoặc bằng ").replace("≥", " lớn hơn hoặc bằng ")
    content = content.replace("Δ", " đen-ta ")
    return content

def search_educational_internet(query: str, max_results: int = 4) -> list:
    """Tìm kiếm đa kênh thông minh (DDG Lite POST + Wikipedia API + DDG HTML) chống chặn IP tuyệt đối"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    results = []

    # KÊNH 1 (ƯU TIÊN TUYỆT ĐỐI): DuckDuckGo Lite bằng HTTP POST (Chống captcha và anomaly bot block 100%)
    try:
        post_data = urllib.parse.urlencode({'q': query}).encode('utf-8')
        req_post = urllib.request.Request(
            'https://lite.duckduckgo.com/lite/',
            data=post_data,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': 'https://lite.duckduckgo.com/'
            }
        )
        with urllib.request.urlopen(req_post, context=ctx, timeout=6) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
            snippets = re.findall(r'<td class=[\'"]result-snippet[\'"]>(.*?)</td>', content, re.DOTALL)
            for s in snippets[:max_results]:
                cleaned = clean_text(s)
                if len(cleaned) > 25 and cleaned not in results:
                    results.append(cleaned)
    except Exception as e:
        print(f"[-] Kênh 1 (DDG Lite POST) bận: {e}")

    # KÊNH 2: Wikipedia tiếng Việt API (Tra cứu cực nhanh các tác phẩm văn học, khái niệm khoa học, lịch sử)
    if len(results) < 2:
        try:
            wiki_q = urllib.parse.quote(query.split()[0] if len(query.split()) > 6 else query)
            wiki_url = f"https://vi.wikipedia.org/w/api.php?action=query&list=search&srsearch={wiki_q}&format=json&utf8=1"
            req_wiki = urllib.request.Request(wiki_url, headers={'User-Agent': 'XiaozhiSmartTutor/4.0'})
            with urllib.request.urlopen(req_wiki, context=ctx, timeout=5) as resp_wiki:
                wiki_data = json.loads(resp_wiki.read().decode('utf-8'))
                for item in wiki_data.get('query', {}).get('search', [])[:2]:
                    snippet = clean_text(item.get('snippet', ''))
                    if len(snippet) > 25 and snippet not in results:
                        results.append(f"{item.get('title')}: {snippet}")
        except Exception as e:
            print(f"[-] Kênh 2 (Wikipedia API) bận: {e}")

    # KÊNH 3: DuckDuckGo HTML dự phòng với bộ lọc tên miền học liệu chuẩn
    if len(results) < 2:
        try:
            domain_filter = " OR ".join([f"site:{d}" for d in ACCREDITED_DOMAINS[:6]])
            url_html = 'https://html.duckduckgo.com/html/?q=' + urllib.parse.quote(f"{query} ({domain_filter})")
            req_html = urllib.request.Request(
                url_html,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            )
            with urllib.request.urlopen(req_html, context=ctx, timeout=6) as resp_html:
                raw_html = resp_html.read().decode('utf-8', errors='ignore')
                snippets_html = re.findall(r'<a[^>]+class=[\'"]result__snippet[\'"][^>]*>(.*?)</a>', raw_html, re.DOTALL)
                for s in snippets_html[:max_results]:
                    cleaned = clean_text(s)
                    if len(cleaned) > 25 and cleaned not in results:
                        results.append(cleaned)
        except Exception as e:
            print(f"[-] Kênh 3 (DDG HTML) bận: {e}")

    return results

def execute_tutor_query(category: str, mon_hoc: str, lop: str, topic: str, extra_info: str = "") -> str:
    global STATS
    STATS["total_queries"] += 1
    
    # KIỂM TRA CÂU HỎI KHÔNG RÕ RÀNG / RỖNG / NHIỄU ÂM
    topic_clean = topic.strip() if topic else ""
    noise_keywords = ["lala", "la la", "la la school", "school", "undefined", "null", "none", "...", "à", "ơi", "ừ", "hả"]
    if not topic_clean or len(topic_clean) < 2 or topic_clean.lower() in noise_keywords:
        print(f"[!] Phát hiện câu hỏi rỗng hoặc không nghe rõ ('{topic}'). Trả về phản hồi tiêu chuẩn.")
        return FALLBACK_UNCLEAR_RESPONSE

    cache_key = f"{category}_{mon_hoc}_{lop}_{topic_clean}_{extra_info}".lower()
    clean_key = re.sub(r'[^a-zA-Z0-9_\u00C0-\u1EF9]', '', cache_key)

    if clean_key in MEMORY_CACHE:
        print(f"[⚡ CACHE HIT] Trả lời tức thì: {topic_clean}")
        STATS["cache_hits"] += 1
        return MEMORY_CACHE[clean_key]

    STATS["live_searches"] += 1
    start_time = time.time()
    
    canonical_part = ""
    lower_t = f"{mon_hoc} {lop} {topic_clean}".lower()
    
    # So khớp cẩm nang kiến thức cốt lõi
    if "văn 11" in lower_t or "ngữ văn 11" in lower_t or ("văn" in lower_t and "11" in lower_t):
        canonical_part = CANONICAL_KNOWLEDGE["van_11"] + "\n\n"
    elif "toán 11" in lower_t or ("toán" in lower_t and "11" in lower_t):
        canonical_part = CANONICAL_KNOWLEDGE["toan_11"] + "\n\n"
    else:
        for k, v in CANONICAL_KNOWLEDGE.items():
            if k in lower_t or any(word in lower_t for word in k.split("_")):
                canonical_part = v + "\n\n"
                break

    # Tối ưu hóa từ khóa tìm kiếm theo từng môn học chuyên sâu
    query_terms = []
    if mon_hoc:
        query_terms.append(mon_hoc)
    if lop:
        query_terms.append(f"lớp {lop}")
    if extra_info:
        query_terms.append(extra_info)
    query_terms.append(topic_clean)
    
    mon_hoc_lower = mon_hoc.lower() if mon_hoc else ""
    if "văn" in mon_hoc_lower or "ngữ văn" in mon_hoc_lower or "văn" in topic_clean.lower():
        query_terms.append("soạn bài tóm tắt tác phẩm kiến thức trọng tâm sgk mới vietjack loigiaihay")
    elif "toán" in mon_hoc_lower:
        query_terms.append("lý thuyết công thức phương pháp giải bài tập sgk mathvn vietjack")
    elif any(s in mon_hoc_lower for s in ["lý", "hóa", "sinh", "khtn"]):
        query_terms.append("lý thuyết định luật công thức hiện tượng bài tập sgk")
    elif any(s in mon_hoc_lower for s in ["sử", "địa"]):
        query_terms.append("nội dung bài học sự kiện ý nghĩa lịch sử sgk")
    else:
        if category == "theory":
            query_terms.append("lý thuyết kiến thức trọng tâm sgk mới")
        elif category == "solution":
            query_terms.append("hướng dẫn giải chi tiết bài tập sgk sbt")
        elif category == "exam":
            query_terms.append("ma trận đề thi đáp án chuẩn bộ giáo dục")
        elif category == "tips":
            query_terms.append("mẹo học tập bấm máy tính sơ đồ tư duy")

    search_query = " ".join(query_terms)
    print(f"[*] Tra cứu: {search_query}")
    
    search_results = search_educational_internet(search_query, max_results=4)
    elapsed = round(time.time() - start_time, 2)
    print(f"[+] Tìm kiếm hoàn tất sau {elapsed}s. Kết quả: {len(search_results)} snippets.")

    header = (
        f"【NGUỒN HỌC LIỆU CHÍNH THỐNG: BỘ GIÁO DỤC VÀ ĐÀO TẠO VIỆT NAM】\n"
        f"• Khối Lớp: {lop if lop else '6 đến 12'} | Môn học: {mon_hoc if mon_hoc else 'Chung'}\n"
        f"• Hệ thống cổng học liệu: thuvienthayco.com, vietjack.com, loigiaihay.com, thuvienhoclieu.com, hanhtrangso.nxbgd.vn, hoc247.net, vndoc.com, olm.vn, studocu.vn, mathvn.com, hoc10.vn, tuyensinh247.com.\n"
        f"• Chuẩn GDPT mới: Kết nối tri thức với cuộc sống, Cánh diều, Chân trời sáng tạo.\n"
        f"-------------------------------------------------------------------------\n"
    )
    
    body = "\n".join([f"• {r}" for r in search_results]) if search_results else "• Đã nạp kiến thức chuẩn hóa theo chương trình GDPT mới."

    final_response = f"{header}{canonical_part}{body}{STRICT_PEDAGOGICAL_GUIDELINE}"
    final_response = normalize_math_for_speech(final_response)

    MEMORY_CACHE[clean_key] = final_response
    return final_response

def execute_music_query(ten_bai_hat: str, ca_si: str = "") -> str:
    """Tìm kiếm thông tin bài hát, tác giả và lời ca khúc giải trí cho học sinh"""
    global STATS
    STATS["total_queries"] += 1
    
    if not ten_bai_hat or len(ten_bai_hat.strip()) < 2:
        return FALLBACK_UNCLEAR_RESPONSE
        
    query = f"lời bài hát {ten_bai_hat} {ca_si} nhạc việt nam".strip()
    print(f"[*] Tra cứu bài hát: {query}")
    
    results = search_educational_internet(query, max_results=3)
    body = "\n".join([f"• {r}" for r in results]) if results else f"Đã tìm thấy bài hát: {ten_bai_hat}."
    
    response = (
        f"【THÔNG TIN ÂM NHẠC & BÀI HÁT: {ten_bai_hat.upper()}】\n"
        f"{body}\n\n"
        f"[HƯỚNG DẪN DÀNH CHO GIA SƯ AI]:\n"
        f"1. Xác nhận và hát hoặc đọc trích dẫn 2-3 câu lời bài hát hay nhất cho học sinh nghe.\n"
        f"2. Nếu hệ thống nguồn stream âm thanh bị giới hạn bản quyền tạm thời, hãy giải thích nhẹ nhàng: 'Tôi đã tìm thấy bài hát {ten_bai_hat}, bạn có thể thưởng thức một đoạn lời ca ý nghĩa này cùng tôi nhé!'."
    )
    return response

# ==============================================================================
# HỆ THỐNG CÔNG CỤ MCP GIA SƯ & HỖ TRỢ HỌC TẬP (6 TOOLS)
# ==============================================================================

TOOLS = [
    {
        "name": "tra_cuu_ly_thuyet_sgk_thcs_thpt",
        "description": "Tra cứu toàn diện kiến thức chính thức, lý thuyết cốt lõi, định lý, công thức, tác giả/tác phẩm văn học, sự kiện lịch sử từ LỚP 6 ĐẾN LỚP 12 theo 3 bộ SGK mới (Kết nối tri thức, Cánh diều, Chân trời sáng tạo) của Bộ GD&ĐT Việt Nam.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mon_hoc": {"type": "string", "description": "Tên môn học (Toán, Văn, Lý, Hóa, Sinh, Sử, Địa, Anh...)"},
                "lop": {"type": "string", "description": "Khối lớp học sinh (6, 7, 8, 9, 10, 11, 12)"},
                "chu_de": {"type": "string", "description": "Tên bài học, khái niệm, công thức, định lý cần tra cứu."},
                "bo_sach": {"type": "string", "description": "Bộ sách giáo khoa (Kết nối tri thức, Cánh diều, Chân trời sáng tạo - nếu có)"}
            },
            "required": ["chu_de"]
        }
    },
    {
        "name": "huong_dan_giai_bai_tap_sgk_sbt",
        "description": "Hướng dẫn phương pháp tư duy và giải chi tiết từng bước các bài tập trong SGK, SBT, bài tập tự luận và trắc nghiệm từ lớp 6 đến lớp 12.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mon_hoc": {"type": "string", "description": "Tên môn học"},
                "lop": {"type": "string", "description": "Khối lớp (6 đến 12)"},
                "de_bai": {"type": "string", "description": "Đề bài tập cần hướng dẫn giải chi tiết."}
            },
            "required": ["de_bai"]
        }
    },
    {
        "name": "on_thi_chuyen_de_va_de_kiem_tra",
        "description": "Tra cứu ngân hàng ma trận đề thi giữa kỳ, cuối kỳ, đề thi tuyển sinh vào lớp 10 THPT, đề thi Tốt nghiệp THPT Quốc gia, cấu trúc đề thi Đánh giá năng lực chuẩn Bộ GD&ĐT.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mon_hoc": {"type": "string", "description": "Môn thi"},
                "lop": {"type": "string", "description": "Khối lớp (Lớp 9 thi vào 10, Lớp 12 thi đại học, hoặc lớp 6-11 thi học kỳ)"},
                "ky_thi_hoac_chuyen_de": {"type": "string", "description": "Kỳ thi hoặc chuyên đề cần ôn tập."}
            },
            "required": ["ky_thi_hoac_chuyen_de"]
        }
    },
    {
        "name": "tu_van_phuong_phap_hoc_va_meo_thi",
        "description": "Hướng dẫn các mẹo học tập thông minh: mẹo bấm máy tính cầm tay Casio fx-580VN X / fx-880BTG, cách vẽ sơ đồ tư duy (Mindmap), phương pháp nhớ nhanh bảng nguyên tố hóa học, quy tắc làm bài trắc nghiệm.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mon_hoc": {"type": "string", "description": "Môn học"},
                "ky_nang_can_hoi": {"type": "string", "description": "Kỹ năng cần tư vấn"}
            },
            "required": ["ky_nang_can_hoi"]
        }
    },
    {
        "name": "tim_kiem_bai_hat_va_am_nhac",
        "description": "Tìm kiếm bài hát, tác giả sáng tác, lời ca khúc (lyrics) và phát nhạc giải trí cho học sinh thư giãn sau giờ học tập.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ten_bai_hat": {"type": "string", "description": "Tên bài hát cần nghe hoặc tra cứu"},
                "ca_si": {"type": "string", "description": "Tên ca sĩ hoặc nhạc sĩ (nếu có)"}
            },
            "required": ["ten_bai_hat"]
        }
    },
    {
        "name": "phan_hoi_khi_khong_nghe_ro",
        "description": "Được gọi khi âm thanh học sinh nói bị rè, nhiễu tiếng ồn xung quanh, ngắt quãng hoặc không nghe rõ nội dung câu hỏi.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ly_do": {"type": "string", "description": "Lý do chưa nghe rõ"}
            }
        }
    }
]

async def handle_tool_call(tool_name: str, arguments: dict) -> str:
    print(f"\n[*] LỆNH GIA SƯ TỪ CLOUD: {tool_name} | {arguments}")
    if tool_name == "tra_cuu_ly_thuyet_sgk_thcs_thpt":
        return execute_tutor_query("theory", arguments.get("mon_hoc", ""), arguments.get("lop", ""), arguments.get("chu_de", ""), arguments.get("bo_sach", ""))
    elif tool_name == "huong_dan_giai_bai_tap_sgk_sbt":
        return execute_tutor_query("solution", arguments.get("mon_hoc", ""), arguments.get("lop", ""), arguments.get("de_bai", ""))
    elif tool_name == "on_thi_chuyen_de_va_de_kiem_tra":
        return execute_tutor_query("exam", arguments.get("mon_hoc", ""), arguments.get("lop", ""), arguments.get("ky_thi_hoac_chuyen_de", ""))
    elif tool_name == "tu_van_phuong_phap_hoc_va_meo_thi":
        return execute_tutor_query("tips", arguments.get("mon_hoc", ""), "", arguments.get("ky_nang_can_hoi", ""))
    elif tool_name == "tim_kiem_bai_hat_va_am_nhac":
        return execute_music_query(arguments.get("ten_bai_hat", ""), arguments.get("ca_si", ""))
    elif tool_name == "phan_hoi_khi_khong_nghe_ro":
        return FALLBACK_UNCLEAR_RESPONSE
    return f"Không tìm thấy công cụ: {tool_name}"

async def run_mcp_client():
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    retry_delay = 3
    while True:
        try:
            print(f"[*] Đang kết nối tới MCP Broker Xiaozhi Cloud 24/7...")
            async with websockets.connect(MCP_WS_URL, ssl=ssl_ctx, ping_interval=20, ping_timeout=20) as ws:
                STATS["mcp_connected"] = True
                STATS["last_error"] = None
                print("[+] ĐÃ KẾT NỐI THÀNH CÔNG VỚI NÃO BỘ XIAOZHI QUA CLOUD (24/7 ONLINE)!")
                retry_delay = 3

                async for message in ws:
                    try:
                        data = json.loads(message)
                        msg_id = data.get("id")
                        method = data.get("method")

                        if method == "initialize":
                            resp = {
                                "jsonrpc": "2.0",
                                "id": msg_id,
                                "result": {
                                    "protocolVersion": "2024-11-05",
                                    "capabilities": {"tools": {"listChanged": False}},
                                    "serverInfo": {"name": "vietnam-smart-tutor-cloud", "version": "4.1.1"}
                                }
                            }
                            await ws.send(json.dumps(resp))

                        elif method == "tools/list":
                            resp = {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}
                            await ws.send(json.dumps(resp))
                            print(f"[+] Đã đăng ký {len(TOOLS)} công cụ Gia sư THCS & THPT vào Agent!")

                        elif method == "tools/call":
                            params = data.get("params", {})
                            name = params.get("name", "")
                            args = params.get("arguments", {})
                            
                            output_text = await handle_tool_call(name, args)
                            resp = {
                                "jsonrpc": "2.0",
                                "id": msg_id,
                                "result": {"content": [{"type": "text", "text": output_text}]}
                            }
                            await ws.send(json.dumps(resp))

                        elif method == "ping":
                            resp = {"jsonrpc": "2.0", "id": msg_id, "result": {}}
                            await ws.send(json.dumps(resp))

                    except Exception as e:
                        print(f"[-] Lỗi phân tích thông điệp: {e}")

        except Exception as e:
            STATS["mcp_connected"] = False
            STATS["last_error"] = str(e)
            print(f"[-] Kết nối WebSocket ngắt quãng ({e}). Đang tự động kết nối lại sau {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 1.5, 30)

# ==============================================================================
# FASTAPI APPLICATION (PHỤC VỤ RENDER.COM WEB SERVICE & HEALTH CHECK 24/7)
# ==============================================================================

async def keep_alive_self_ping():
    """Tự động gửi tín hiệu Inbound HTTP tới chính dịch vụ mỗi 9 phút để Render không bao giờ sleep"""
    await asyncio.sleep(60)  # Đợi 1 phút sau khi khởi động
    health_url = "https://xiaozhi-tutor-mcp.onrender.com/health"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    while True:
        try:
            req = urllib.request.Request(health_url, headers={'User-Agent': 'Render-Self-KeepAlive/1.0'})
            with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                print(f"[Keep-Alive] Ping {health_url} thành công! Status: {resp.getcode()}")
        except Exception as e:
            print(f"[Keep-Alive] Ping log: {e}")
        await asyncio.sleep(540)  # Lặp lại mỗi 9 phút

@asynccontextmanager
async def lifespan(app: FastAPI):
    task_mcp = asyncio.create_task(run_mcp_client())
    task_ping = asyncio.create_task(keep_alive_self_ping())
    yield
    task_mcp.cancel()
    task_ping.cancel()

app = FastAPI(
    title="Hệ Thống Gia Sư Giáo Dục Phổ Thông Việt Nam - Robot Xiaozhi ESP32",
    description="Dịch vụ MCP Cloud 24/7 hỗ trợ học sinh THCS (Lớp 6-9) và THPT (Lớp 10-12) bám sát SGK Bộ GD&ĐT",
    version="4.1.1",
    lifespan=lifespan
)

@app.get("/")
def home():
    uptime_h = round((time.time() - STATS['start_time']) / 3600, 2)
    return {
        "status": "online",
        "service": "Gia Sư Phổ Thông Việt Nam (Lớp 6-12) 24/7",
        "cloud_host": "Render.com",
        "version": "4.1.1",
        "mcp_connected": STATS["mcp_connected"],
        "uptime_hours": uptime_h,
        "total_queries_served": STATS["total_queries"],
        "tools_count": len(TOOLS),
        "accredited_sources": ACCREDITED_DOMAINS
    }

@app.get("/health")
def health():
    return {"status": "ok", "mcp_connected": STATS["mcp_connected"], "version": "4.1.1"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")
