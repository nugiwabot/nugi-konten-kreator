import os
import json
import urllib.request
import urllib.parse
import time

MCP_URL = "https://mcp.pexafy.com/mcp"
def get_pexafy_token():
    token = os.environ.get("PEXAFY_API_KEY")
    if token:
        return token
    config_path = os.path.expanduser(r"~/.gemini/config/mcp_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                auth = data.get("mcpServers", {}).get("pexafy", {}).get("headers", {}).get("Authorization", "")
                if auth.startswith("Bearer "):
                    return auth.split("Bearer ")[1].strip()
                return auth.strip()
        except Exception:
            pass
    return ""

TOKEN = get_pexafy_token()

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/event-stream"
}

def init_mcp_session():
    init_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "pexafy-microbeat-master-part3", "version": "1.0"}
        }
    }
    req = urllib.request.Request(MCP_URL, data=json.dumps(init_payload).encode("utf-8"), headers=HEADERS, method="POST")
    with urllib.request.urlopen(req) as resp:
        session_id = resp.headers.get("mcp-session-id")
    print(f"MCP Session Initialized: {session_id}")
    return session_id

def search_photos(session_id, query, orientation="portrait"):
    headers = dict(HEADERS)
    if session_id:
        headers["mcp-session-id"] = session_id
        
    call_payload = {
        "jsonrpc": "2.0",
        "id": int(time.time() * 1000) % 100000,
        "method": "tools/call",
        "params": {
            "name": "search_photos",
            "arguments": {
                "q": query,
                "orientation": orientation
            }
        }
    }
    req = urllib.request.Request(MCP_URL, data=json.dumps(call_payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        for line in resp.read().decode("utf-8").splitlines():
            if line.startswith("data: "):
                res = json.loads(line[6:])
                text_content = res.get("result", {}).get("content", [{}])[0].get("text", "{}")
                parsed = json.loads(text_content)
                return parsed.get("data", [])
    return []

def download_image(url, target_path):
    headers = {"User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        content = resp.read()
    with open(target_path, "wb") as f:
        f.write(content)
    return len(content)

MICROBEATS_06_TO_15 = [
    {
        "id": "narasi-06",
        "title": "Mengapa Anak yang Terlalu Cepat Diajari AI Berisiko Kehilangan Daya Pikirnya?",
        "pillar": "AI × HUMAN × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-06",
        "beats": [
            {"file_name": "beat_01_00-02s_child_tablet_fast.jpg", "duration": "2s", "timestamp": "00:00 - 00:02", "shot_type": "Close-Up Screen", "script_line": "Banyak orang tua bangga banget...", "visual_concept": "Anak SD menatap tablet digital dengan mata berbinar", "search_query": "close up elementary child looking at glowing digital tablet learning", "editor_note": "Cut kilat 2 detik pembuka."},
            {"file_name": "beat_02_02-05s_ai_homework_prompt.jpg", "duration": "3s", "timestamp": "00:02 - 00:05", "shot_type": "POV Tablet", "script_line": "...pas ngeliat anaknya yang masih SD udah jago pakai AI buat ngerjain PR dan bikin tugas sekolah.", "visual_concept": "Aplikasi AI di tablet memunculkan jawaban tugas sekolah instan", "search_query": "digital screen showing ai assistant generating homework answers fast", "editor_note": "Jawaban tugas muncul dalam sekejap."},
            {"file_name": "beat_03_05-08s_instant_glow_addiction.jpg", "duration": "3s", "timestamp": "00:05 - 00:08", "shot_type": "Dark Portrait", "script_line": "Kelihatannya keren dan melek teknologi.", "visual_concept": "Wajah anak terpapar cahaya biru layar gadget dalam kegelapan", "search_query": "child face illuminated in dark by blue screen light tech addiction", "editor_note": "Pencahayaan dingin di wajah anak."},
            {"file_name": "beat_04_08-12s_killing_deep_cognition.jpg", "duration": "4s", "timestamp": "00:08 - 00:12", "shot_type": "Conceptual Macro", "script_line": "Tapi kalau kita amati riset perkembangan otak anak, kebiasaan mendapatkan jawaban instan dalam lima detik justru diam-diam mematikan satu kemampuan paling mendasar manusia.", "visual_concept": "Pensil patah di atas lembar soal matematika yang belum selesai", "search_query": "broken pencil lead on paper math homework frustration", "editor_note": "Pensil patah di atas kertas soal."},
            {"file_name": "beat_05_12-16s_math_scratch_frustration.jpg", "duration": "4s", "timestamp": "00:12 - 00:16", "shot_type": "Over-The-Shoulder", "script_line": "Otak anak tidak membangun kecerdasan dari jawaban yang benar. Otak membangun kecerdasan dari proses kebingungan...", "visual_concept": "Anak menopang dagu dengan pensil menghadap kertas coretan rumus", "search_query": "frustrated child doing difficult math homework scratch paper thinking hard", "editor_note": "Proses bergulat dengan soal sulit."},
            {"file_name": "beat_06_16-20s_erasing_and_retrying.jpg", "duration": "4s", "timestamp": "00:16 - 00:20", "shot_type": "Close-Up Hand", "script_line": "...rasa mentok saat hitungan matematika nggak ketemu, coret-coret kertas berkali-kali...", "visual_concept": "Tangan anak menghapus coretan salah dan mencoba menulis lagi", "search_query": "child hand erasing mistakes on paper with eraser grit persistence", "editor_note": "Menghapus dan mencoba lagi, proses biologis belajar."},
            {"file_name": "beat_07_20-25s_eureka_puzzle_block.jpg", "duration": "5s", "timestamp": "00:20 - 00:25", "shot_type": "Eureka Moment", "script_line": "...dan kegigihan mencoba lagi sampai polanya terbuka. Di momen frustrasi itulah sinapsis saraf baru terbentuk.", "visual_concept": "Mata anak berbinar senang saat balok logika berhasil tersusun rapi", "search_query": "happy child solving wooden block puzzle eureka moment achievement bright eyes", "editor_note": "Senyum kepuasan saat berhasil memecahkan teka-teki."},
            {"file_name": "beat_08_25-29s_fragile_screen_generation.jpg", "duration": "4s", "timestamp": "00:25 - 00:29", "shot_type": "Moody Side Profile", "script_line": "Saat anak dibiasakan minta jawaban ke AI setiap kali menghadapi soal sulit, kita bukan sedang melahirkan generasi jenius.", "visual_concept": "Anak tampak murung dan tidak sabar saat gadget diambil", "search_query": "impatient child waiting for screen loading unhappy emotional fragility", "editor_note": "Kerapuhan emosional saat tidak ada jawaban instan."},
            {"file_name": "beat_09_29-34s_rainy_window_fragility.jpg", "duration": "5s", "timestamp": "00:29 - 00:34", "shot_type": "Cinematic Mood", "script_line": "Kita sedang melatih generasi yang tidak punya daya tahan mental saat dunia nyata tidak memberikan jawaban instan.", "visual_concept": "Anak menatap keluar kaca jendela saat rintik hujan turun dengan rasa gamang", "search_query": "child looking out rainy window glass feeling lonely overwhelmed resilience", "editor_note": "Slow zoom out anak menatap hujan."},
            {"file_name": "beat_10_34-39s_sitting_with_unsolved_puzzle.jpg", "duration": "5s", "timestamp": "00:34 - 00:39", "shot_type": "Calm Reflection", "script_line": "Kalau jawaban bisa dicari dalam sedetik oleh mesin, bukankah keahlian termahal anak kita nanti adalah keberanian untuk duduk tenang memikirkan teka-teki yang belum ada jawabannya?", "visual_concept": "Anak duduk tenang di karpet merenungkan teka-teki kayu tanpa tergesa-gesa", "search_query": "child sitting quietly on floor thoughtfully examining unsolved wooden puzzle", "editor_note": "Duduk tenang memikirkan teka-teki yang belum ada jawabannya."},
            {"file_name": "beat_11_39-45s_reading_under_sunlit_tree.jpg", "duration": "6s", "timestamp": "00:39 - 00:45", "shot_type": "Peaceful Outdoor", "script_line": "Menurut Anda gimana?", "visual_concept": "Anak membaca buku cerita fisik di bawah naungan pohon rindang bermandikan cahaya matahari pagi", "search_query": "young child reading physical storybook under big shady tree peaceful morning sunlight", "editor_note": "Membaca buku fisik di bawah pohon rindang. Fade out."}
        ]
    },
    {
        "id": "narasi-07",
        "title": "Saat Beli Rumah, Sebenarnya Kita Sedang Membayar Siapa Tetangga Kita",
        "pillar": "PROPERTY × HUMAN × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-07",
        "beats": [
            {"file_name": "beat_01_00-03s_two_identical_houses.jpg", "duration": "3s", "timestamp": "00:00 - 00:03", "shot_type": "Symmetrical Architecture", "script_line": "Pernah kepikiran nggak, kenapa dua rumah dengan ukuran tanah dan kualitas semen bata yang sama persis...", "visual_concept": "Dua rumah modern berdampingan dengan bentuk dan bahan bata yang mirip", "search_query": "two identical modern brick residential houses standing side by side suburb", "editor_note": "Dua rumah kembar berdampingan."},
            {"file_name": "beat_02_03-06s_price_gap_hundred_millions.jpg", "duration": "3s", "timestamp": "00:03 - 00:06", "shot_type": "Close-Up Document", "script_line": "...harganya bisa beda sampai ratusan juta rupiah?", "visual_concept": "Brosur harga properti dengan perbedaan angka ratusan juta rupiah", "search_query": "real estate price contract comparison difference paperwork pen", "editor_note": "Perbedaan harga yang mencolok."},
            {"file_name": "beat_03_06-09s_marketing_buzzwords.jpg", "duration": "3s", "timestamp": "00:06 - 00:09", "shot_type": "Glossy Brochure", "script_line": "Brosur marketing biasanya nyebut ini faktor 'lokasi strategis' atau 'desain eksklusif'.", "visual_concept": "Brosur perumahan mewah mengkilap dengan tulisan 'Exclusive Living'", "search_query": "luxury real estate sales brochure brochure cover glossy architecture", "editor_note": "Brosur glossy marketing."},
            {"file_name": "beat_04_09-13s_exclusive_security_gate.jpg", "duration": "4s", "timestamp": "00:09 - 00:13", "shot_type": "Low Angle Gate", "script_line": "Tapi kalau kita jujur pada psikologi manusia, ada satu hal tak kasat mata yang diam-diam kita bayar sangat mahal: kita sedang membayar siapa orang yang tinggal di sebelah kita.", "visual_concept": "Gerbang gerbang kluster mewah tertutup dengan pos keamanan modern", "search_query": "grand gated community security entrance boom barrier private upscale cluster", "editor_note": "Gerbang eksklusif perumahan mewah."},
            {"file_name": "beat_05_13-17s_tribal_belonging_fear.jpg", "duration": "4s", "timestamp": "00:13 - 00:17", "shot_type": "Moody Social", "script_line": "Sejak zaman purba, manusia selalu dihantui oleh ketakutan diasingkan dari kelompok.", "visual_concept": "Siluet seseorang berdiri terisolasi di luar lingkaran kelompok manusia", "search_query": "silhouette person standing isolated outside circle of people primal belonging", "editor_note": "Ketakutan diasingkan dari kelompok."},
            {"file_name": "beat_06_17-21s_cluster_kids_bicycles.jpg", "duration": "4s", "timestamp": "00:17 - 00:21", "shot_type": "Wholesome Suburban", "script_line": "Di era modern, rumah bukan lagi sekadar pelindung dari hujan. Alamat rumah dan gerbang komplek telah menjadi seragam sosial tak tertulis untuk menyaring siapa kawan bermain anak kita...", "visual_concept": "Anak-anak bersepeda gembira di jalanan kluster aspal bersih yang aman", "search_query": "suburban neighborhood children riding bicycles laughing safe private street", "editor_note": "Anak-anak bermain di jalanan kluster rapi."},
            {"file_name": "beat_07_21-25s_status_signaling_cars.jpg", "duration": "4s", "timestamp": "00:21 - 00:25", "shot_type": "Status Luxury", "script_line": "...dan bagaimana keluarga besar menilai stabilitas hidup kita.", "visual_concept": "Mobil mewah terparkir rapi di carport rumah kluster modern 2 lantai", "search_query": "modern upscale house driveway luxury suv car parked outside architectural home", "editor_note": "Sinyal status sosial dan stabilitas."},
            {"file_name": "beat_08_25-30s_status_anxiety_curtains.jpg", "duration": "5s", "timestamp": "00:25 - 00:30", "shot_type": "Psychological Interior", "script_line": "Jadi saat orang rela mencicil miliaran rupiah di sebuah kluster tertutup, mereka sebenarnya tidak membeli batu bata. Mereka sedang membeli rasa aman dari kecemasan status mereka sendiri...", "visual_concept": "Pemilik rumah mengintip dari balik tirai jendela mewah dengan pandangan waspada", "search_query": "person peering through venetian blinds upscale modern house anxious guarded", "editor_note": "Mengintip dari balik tirai: kecemasan status."},
            {"file_name": "beat_09_30-35s_like_minded_bubble.jpg", "duration": "5s", "timestamp": "00:30 - 00:35", "shot_type": "Enclosed Neighborhood", "script_line": "...ingin memastikan bahwa mereka berada di lingkungan orang-orang yang sepemikiran.", "visual_concept": "Deretan rumah bertembok tinggi seragam yang terisolasi dari kampung luar", "search_query": "high walled cluster housing identical facade isolated gated neighborhood", "editor_note": "Lingkungan orang-orang sepemikiran di dalam gelembung sosial."},
            {"file_name": "beat_10_35-41s_towering_compound_wall.jpg", "duration": "6s", "timestamp": "00:35 - 00:41", "shot_type": "Cold Divide", "script_line": "Pertanyaannya: apakah dinding komplek yang tinggi itu benar-benar melindungi kedamaian keluarga kita, atau kita cuma sedang mengurung diri dari dunia nyata?", "visual_concept": "Tembok beton tinggi pembatas kluster di bawah langit senja abu-abu", "search_query": "tall concrete perimeter wall with wire fence dividing neighborhood twilight", "editor_note": "Tembok beton tinggi di kala senja. Fade out."}
        ]
    },
    {
        "id": "narasi-08",
        "title": "Ketika Rumah Pintar Tahu Semua Rahasia Kamar Tidur Kita",
        "pillar": "AI × PROPERTY × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-08",
        "beats": [
            {"file_name": "beat_01_00-03s_double_deadbolt_lock.jpg", "duration": "3s", "timestamp": "00:00 - 00:03", "shot_type": "Close-Up Security", "script_line": "Coba perhatikan ironi ini: kita pasang gembok pintu ganda biar orang asing nggak masuk ke rumah...", "visual_concept": "Gembok pintu baja ganda terkunci rapat di pintu depan rumah", "search_query": "heavy double deadbolt door lock secure brass keyhole front entrance", "editor_note": "Gembok pintu ganda kokoh."},
            {"file_name": "beat_02_03-06s_smart_camera_nightstand.jpg", "duration": "3s", "timestamp": "00:03 - 00:06", "shot_type": "Tech Detail", "script_line": "...tapi sukarela pasang mikrofon dan kamera cloud pintar di kamar tidur kita sendiri.", "visual_concept": "Kamera pintar mungil dengan cincin cahaya biru menyala di nakas kamar tidur", "search_query": "smart home security camera glowing blue led lens on bedroom nightstand", "editor_note": "Kamera pintar di nakas kamar tidur."},
            {"file_name": "beat_03_06-10s_automated_comfort_lights.jpg", "duration": "4s", "timestamp": "00:06 - 00:10", "shot_type": "Ambient Motion", "script_line": "Semua atas nama kenyamanan: lampu nyala otomatis pas kita masuk ruangan, AC menyesuaikan suhu tubuh, dan asisten suara memutar lagu favorit tanpa disentuh.", "visual_concept": "Lampu kamar tidur pintar otomatis menyala lembut saat langkah kaki masuk", "search_query": "ambient smart home lights automatically turning on walking into modern room", "editor_note": "Kenyamanan serba otomatis."},
            {"file_name": "beat_04_10-14s_lost_sanctuary_question.jpg", "duration": "4s", "timestamp": "00:10 - 00:14", "shot_type": "Moody Shadow", "script_line": "Tapi pernah nggak kita renungkan, apa yang diam-diam hilang dari rumah kita?", "visual_concept": "Siluet seseorang menatap cermin kamar mandi dengan tatapan bimbang", "search_query": "silhouette person looking at bathroom mirror in dim moody light lost sanctuary", "editor_note": "Apa yang diam-diam hilang dari rumah kita?"},
            {"file_name": "beat_05_14-18s_unmasked_vulnerability_bed.jpg", "duration": "4s", "timestamp": "00:14 - 00:18", "shot_type": "Intimate Emotional", "script_line": "Secara naluri biologis, rumah adalah satu-satunya benteng terakhir di muka bumi di mana manusia bisa melepas semua topeng sosial.", "visual_concept": "Seseorang duduk bersandar di ranjang dengan selimut berantakan dan ekspresi lelah jujur", "search_query": "person sitting on bed messy sheets authentic tired face no social mask safe", "editor_note": "Tempat melepas semua topeng sosial."},
            {"file_name": "beat_06_18-23s_safe_to_weep_quiet.jpg", "duration": "5s", "timestamp": "00:18 - 00:23", "shot_type": "Emotional Solitude", "script_line": "Tempat di mana kita bebas terlihat lelah, menangis, bertengkar dengan pasangan, atau tidur berantakan tanpa ada mata yang menilai.", "visual_concept": "Seseorang mendekap lutut di sudut ranjang dalam keheningan kamar yang aman", "search_query": "person sitting alone in dark cozy bedroom hugging knees emotional relief", "editor_note": "Bebas terlihat lelah dan menangis tanpa ada mata yang menilai."},
            {"file_name": "beat_07_23-28s_iot_sensors_blinking_red.jpg", "duration": "5s", "timestamp": "00:23 - 00:28", "shot_type": "Ominous Tech", "script_line": "Ketika setiap dinding dan sudut rumah dipenuhi sensor algoritma yang terus merekam data ke server komputasi, tanpa sadar tubuh kita tidak pernah benar-benar rileks.", "visual_concept": "Sensor IoT berkedip merah kecil di sudut plafon kamar di malam hari", "search_query": "small red blinking surveillance sensor light on dark ceiling ceiling corner", "editor_note": "Sensor berkedip merah: tubuh tidak pernah benar-benar rileks."},
            {"file_name": "beat_08_28-33s_digital_showroom_cage.jpg", "duration": "5s", "timestamp": "00:28 - 00:33", "shot_type": "Glass Reflection", "script_line": "Benteng perlindungan kita telah berubah menjadi ruang pameran digital yang selalu terhubung.", "visual_concept": "Pantulan seseorang di dinding kaca apartemen malam hari dikelilingi gelombang data", "search_query": "person reflection in glass apartment window surrounded by city lights connected cage", "editor_note": "Ruang pameran digital yang selalu terhubung."},
            {"file_name": "beat_09_33-39s_unplugged_mountain_solitude.jpg", "duration": "6s", "timestamp": "00:39 - 00:45", "shot_type": "Pure Freedom", "script_line": "Kalau rumah pintar kita tahu semua rutinitas pribadi kita, di mana lagi tempat di bumi ini di mana kita bisa benar-benar sendirian dan bebas?", "visual_concept": "Seseorang duduk sendirian di tepi tebing danau alam tanpa listrik atau kabel di bawah bintang", "search_query": "lone person sitting on quiet mountain cliff looking at stars truly alone freedom", "editor_note": "Benar-benar sendirian dan bebas di alam. Fade out."}
        ]
    }
]

def main():
    session_id = init_mcp_session()
    
    for plan in MICROBEATS_06_TO_15:
        narasi_id = plan["id"]
        narasi_title = plan["title"]
        assets_dir = os.path.join(plan["folder"], "assets")
        os.makedirs(assets_dir, exist_ok=True)
        
        print(f"\n=======================================================")
        print(f"EXPANDING MICRO-BEATS: {narasi_id} ({len(plan['beats'])} dynamic cuts)")
        print(f"Target folder: {assets_dir}")
        print(f"=======================================================")
        
        for idx, beat in enumerate(plan["beats"]):
            file_name = beat["file_name"]
            target_path = os.path.join(assets_dir, file_name)
            
            if os.path.exists(target_path) and os.path.getsize(target_path) > 10000:
                print(f"[{idx+1}/{len(plan['beats'])}] Already exists: {file_name}")
                continue
                
            query = beat["search_query"]
            shot_type = beat.get("shot_type", "Visual Cut")
            duration = beat.get("duration", "3s")
            print(f"\n[{idx+1}/{len(plan['beats'])}] [{duration} | {shot_type}] Searching: '{query}'...")
            
            try:
                results = search_photos(session_id, query, orientation="portrait")
                if not results:
                    results = search_photos(session_id, query[:45], orientation="portrait")
                
                if results:
                    chosen = results[0]
                    urls = chosen.get("urls", {})
                    img_url = urls.get("large") or urls.get("regular") or urls.get("full") or chosen.get("image_url")
                    
                    size_bytes = download_image(img_url, target_path)
                    print(f"  Saved {file_name} ({size_bytes:,} bytes)")
                else:
                    print(f"  Warning: No image found for {file_name}")
            except Exception as e:
                print(f"  Error downloading beat {file_name}: {e}")
            
            time.sleep(0.3)
            
        # Update SCRIPT_AND_STORYBOARD.md with microbeats
        storyboard_path = os.path.join(plan["folder"], "SCRIPT_AND_STORYBOARD.md")
        with open(storyboard_path, "w", encoding="utf-8") as f:
            f.write(f"# 🎬 Storyboard Micro-Beat Dinamis: {narasi_title}\n\n")
            f.write(f"**Pilar Konten:** `{plan['pillar']}`  \n")
            f.write(f"**Pola Editing:** Dynamic Asymmetrical Rhythm (Potongan gambar berganti setiap **2 - 5 Detik**, non-linear/tidak monoton)  \n")
            f.write(f"**Format Output:** 9:16 Vertical Video (TikTok / Shorts / Reels)  \n\n")
            f.write(f"---\n\n")
            f.write(f"## 🎞️ Timeline Micro-Beat Sekuensial (Editing Cue Sheet)\n\n")
            f.write(f"| Beat # | Durasi | Timestamp | Tipe Shot | File Aset B-Roll | Baris Naskah | Panduan Kamera & Editor |\n")
            f.write(f"| :---: | :---: | :---: | :---: | :--- | :--- | :--- |\n")
            for idx, b in enumerate(plan["beats"]):
                f.write(f"| **{idx+1:02d}** | `{b.get('duration','3s')}` | `{b.get('timestamp','')}` | *{b.get('shot_type','Visual')}* | [`assets/{b['file_name']}`](file:///{plan['folder'].replace(chr(92),'/')}/assets/{b['file_name']}) | \"{b.get('script_line','')}\" | {b.get('editor_note', b.get('b_roll_cue',''))} |\n")
            f.write(f"\n---\n\n")
            f.write(f"## 📜 Naskah Lengkap Berbasis Micro-Beats (2–5 Detik Cuts)\n\n")
            for idx, b in enumerate(plan["beats"]):
                f.write(f"#### Beat {idx+1:02d} `[{b.get('timestamp','')}]` ({b.get('duration','3s')} cut - *{b.get('shot_type','')}*)\n")
                f.write(f"> **NUGI (Talking Head / Voice):**\n")
                f.write(f"> \"{b.get('script_line','')}\"\n\n")
                f.write(f"- 🎬 **Visual Cut:** `assets/{b['file_name']}`\n")
                f.write(f"- 💡 **Konsep Visual:** {b.get('visual_concept','')}\n")
                f.write(f"- ✂️ **Instruksi Editing:** {b.get('editor_note', b.get('b_roll_cue',''))}\n\n")
                
        print(f"Generated dynamic micro-beat storyboard: {storyboard_path}")

if __name__ == "__main__":
    main()
