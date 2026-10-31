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
    "vietjack.com",
    "loigiaihay.com",
    "hoc247.net",
    "vndoc.com",
    "hanhtrangso.nxbgd.vn",
    "hoc10.vn",
    "tuyensinh247.com",
    "thuvienhoclieu.com",
    "olm.vn"
]

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
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }

    domain_filter = " OR ".join([f"site:{d}" for d in ACCREDITED_DOMAINS[:5]])
    url1 = 'https://html.duckduckgo.com/html/?q=' + urllib.parse.quote(f"{query} ({domain_filter})")
    
    results = []
    try:
        req = urllib.request.Request(url1, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=7) as resp:
            raw = resp.read().decode('utf-8', errors='ignore')
            snippets = re.findall(r'<a[^>]+class=[\'"]result__snippet[\'"][^>]*>(.*?)</a>', raw, re.DOTALL)
            for s in snippets[:max_results]:
                cleaned = clean_text(s)
                if len(cleaned) > 25 and cleaned not in results:
                    results.append(cleaned)
    except Exception as e:
        print(f"[-] Kênh chính bận: {e}")

    if len(results) < 2:
        url2 = 'https://html.duckduckgo.com/html/?q=' + urllib.parse.quote(f"{query} sách giáo khoa chương trình mới bộ giáo dục kết nối tri thức cánh diều chân trời sáng tạo")
        try:
            req2 = urllib.request.Request(url2, headers=headers)
            with urllib.request.urlopen(req2, context=ctx, timeout=7) as resp2:
                raw2 = resp2.read().decode('utf-8', errors='ignore')
                snippets2 = re.findall(r'<a[^>]+class=[\'"]result__snippet[\'"][^>]*>(.*?)</a>', raw2, re.DOTALL)
                for s in snippets2[:max_results]:
                    cleaned2 = clean_text(s)
                    if len(cleaned2) > 25 and cleaned2 not in results:
                        results.append(cleaned2)
        except Exception as e:
            print(f"[-] Kênh mở rộng bận: {e}")

    return results

def execute_tutor_query(category: str, mon_hoc: str, lop: str, topic: str, extra_info: str = "") -> str:
    global STATS
    STATS["total_queries"] += 1
    
    cache_key = f"{category}_{mon_hoc}_{lop}_{topic}_{extra_info}".lower()
    clean_key = re.sub(r'[^a-zA-Z0-9_\u00C0-\u1EF9]', '', cache_key)

    if clean_key in MEMORY_CACHE:
        print(f"[⚡ CACHE HIT] Trả lời tức thì: {topic}")
        STATS["cache_hits"] += 1
        return MEMORY_CACHE[clean_key]

    STATS["live_searches"] += 1
    start_time = time.time()
    
    canonical_part = ""
    lower_t = topic.lower()
    for k, v in CANONICAL_KNOWLEDGE.items():
        if k in lower_t or any(word in lower_t for word in k.split("_")):
            canonical_part = v + "\n\n"
            break

    query_terms = []
    if mon_hoc:
        query_terms.append(mon_hoc)
    if lop:
        query_terms.append(f"lớp {lop}")
    if extra_info:
        query_terms.append(extra_info)
    query_terms.append(topic)
    
    if category == "theory":
        query_terms.append("lý thuyết định nghĩa công thức sgk")
    elif category == "solution":
        query_terms.append("hướng dẫn giải bài tập sgk sbt chi tiết")
    elif category == "exam":
        query_terms.append("ma trận đề thi đáp án chuẩn bộ giáo dục")
    elif category == "tips":
        query_terms.append("mẹo bấm máy tính casio cách nhớ nhanh sơ đồ tư duy")

    search_query = " ".join(query_terms)
    print(f"[*] Tra cứu: {search_query}")
    
    search_results = search_educational_internet(search_query, max_results=4)
    elapsed = round(time.time() - start_time, 2)
    print(f"[+] Tìm kiếm hoàn tất sau {elapsed}s.")

    header = (
        f"【NGUỒN HỌC LIỆU CHÍNH THỐNG: BỘ GIÁO DỤC VÀ ĐÀO TẠO VIỆT NAM】\n"
        f"• Khối Lớp: {lop if lop else '6 đến 12'} | Môn học: {mon_hoc if mon_hoc else 'Chung'}\n"
        f"• Chuẩn GDPT mới: Kết nối tri thức với cuộc sống, Cánh diều, Chân trời sáng tạo.\n"
        f"-------------------------------------------------------------------------\n"
    )
    
    body = "\n".join([f"• {r}" for r in search_results])
    
    guideline = (
        "\n\n[QUY TẮC SƯ PHẠM DÀNH CHO GIA SƯ AI XIAOZHI]:\n"
        "1. Giảng giải 4 bước: Bản chất khái niệm -> Công thức/Quy tắc -> Ví dụ bài tập mẫu -> Lưu ý lỗi sai thường gặp khi đi thi.\n"
        "2. Dùng giọng điệu người thầy tận tụy, ấm áp, khuyến khích học sinh tự giác tư duy."
    )

    final_response = f"{header}{canonical_part}{body}{guideline}"
    final_response = normalize_math_for_speech(final_response)

    MEMORY_CACHE[clean_key] = final_response
    return final_response

TOOLS = [
    {
        "name": "tra_cuu_ly_thuyet_sgk_thcs_thpt",
        "description": "Tra cứu toàn diện kiến thức chính thức, lý thuyết cốt lõi, định lý, công thức, định nghĩa, tác giả/tác phẩm văn học, sự kiện lịch sử từ LỚP 6 ĐẾN LỚP 12 theo 3 bộ sách giáo khoa mới (Kết nối tri thức, Cánh diều, Chân trời sáng tạo) của Bộ Giáo dục và Đào tạo Việt Nam.",
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
        "description": "Hướng dẫn phương pháp tư duy và giải chi tiết từng bước các bài tập trong Sách giáo khoa (SGK), Sách bài tập (SBT), bài tập tự luận và trắc nghiệm từ lớp 6 đến lớp 12.",
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
                                    "serverInfo": {"name": "vietnam-smart-tutor-cloud", "version": "4.0.0"}
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
    # Khởi động tiến trình MCP client và tiến trình Keep-Alive chạy ngầm vĩnh viễn trên Cloud
    task_mcp = asyncio.create_task(run_mcp_client())
    task_ping = asyncio.create_task(keep_alive_self_ping())
    yield
    task_mcp.cancel()
    task_ping.cancel()


app = FastAPI(
    title="Hệ Thống Gia Sư Giáo Dục Phổ Thông Việt Nam - Robot Xiaozhi ESP32",
    description="Dịch vụ MCP Cloud 24/7 hỗ trợ học sinh THCS (Lớp 6-9) và THPT (Lớp 10-12) bám sát SGK Bộ GD&ĐT",
    version="4.0.0",
    lifespan=lifespan
)

@app.get("/")
def home():
    uptime_h = round((time.time() - STATS['start_time']) / 3600, 2)
    return {
        "status": "online",
        "service": "Gia Sư Phổ Thông Việt Nam (Lớp 6-12) 24/7",
        "cloud_host": "Render.com",
        "mcp_connected": STATS["mcp_connected"],
        "uptime_hours": uptime_h,
        "total_queries_served": STATS["total_queries"],
        "tools_count": len(TOOLS),
        "accredited_sources": ACCREDITED_DOMAINS[:5]
    }

@app.get("/health")
def health():
    return {"status": "ok", "mcp_connected": STATS["mcp_connected"]}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")
