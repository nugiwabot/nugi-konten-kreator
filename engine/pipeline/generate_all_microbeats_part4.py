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
            "clientInfo": {"name": "pexafy-microbeat-master-part4", "version": "1.0"}
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

MICROBEATS_09_TO_12 = [
    {
        "id": "narasi-09",
        "title": "Mengapa Portofolio Gambar dan Koding Sekarang Kehilangan Nilainya?",
        "pillar": "WORK × AI × HUMAN × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-09",
        "beats": [
            {"file_name": "beat_01_00-02s_flawless_portfolio_scroll.jpg", "duration": "2s", "timestamp": "00:00 - 00:02", "shot_type": "Close-Up Screen", "script_line": "Kalau Anda masih bangga pamer portofolio...", "visual_concept": "Tampilan website portofolio grafis dan kode koding yang sangat mulus di laptop", "search_query": "laptop screen displaying sleek digital design portfolio clean code", "editor_note": "Cut pembuka kilat 2 detik."},
            {"file_name": "beat_02_02-05s_expired_proof_concept.jpg", "duration": "3s", "timestamp": "00:02 - 00:05", "shot_type": "Metaphorical Concept", "script_line": "...desain yang mulus atau baris kode yang rapi saat melamar kerja, hati-hati: cara pembuktian itu baru saja kedaluwarsa.", "visual_concept": "Kertas sertifikat atau ijazah tersiram air pudar berdebu", "search_query": "faded antique certificate paper blurred obsolete credential concept", "editor_note": "Visual pembuktian lama yang telah kedaluwarsa."},
            {"file_name": "beat_03_05-08s_thirty_second_prompt.jpg", "duration": "3s", "timestamp": "00:05 - 00:08", "shot_type": "Fast Hands Typing", "script_line": "Dulu, portofolio yang indah adalah tiket emas untuk meyakinkan klien atau atasan. Tapi hari ini...", "visual_concept": "Jemari mengetik cepat satu baris prompt sederhana di kotak input AI", "search_query": "hands typing short text prompt on keyboard ai interface screen", "editor_note": "Tangan mengetik prompt kilat 30 detik."},
            {"file_name": "beat_04_08-12s_instant_masterpiece_spawn.jpg", "duration": "4s", "timestamp": "00:08 - 00:12", "shot_type": "Abstract Render", "script_line": "...siapa pun yang bisa menulis prompt selama tiga puluh detik bisa menghasilkan portofolio visual yang terlihat seperti karya profesional berpengalaman sepuluh tahun.", "visual_concept": "Ilustrasi digital 3D megah seketika tercipta di layar dengan detail memukau", "search_query": "masterpiece digital 3d artwork rendered instantly futuristic visual screen", "editor_note": "Karya profesional 10 tahun tercipta seketika."},
            {"file_name": "beat_05_12-16s_worthless_abundance_graph.jpg", "duration": "4s", "timestamp": "00:12 - 00:16", "shot_type": "Data Crash", "script_line": "Ketika hasil akhir karya (the output) bisa dibuat dalam sekejap tanpa biaya oleh kecerdasan buatan, nilai pasar dari output itu otomatis anjlok mendekati nol.", "visual_concept": "Grafik ekonomi nilai output jatuh mendekati titik nol rupiah", "search_query": "digital downward graph plummeting value zero cost abundance economy", "editor_note": "Nilai output anjlok mendekati nol."},
            {"file_name": "beat_06_16-20s_unimpressed_client_meeting.jpg", "duration": "4s", "timestamp": "00:16 - 00:20", "shot_type": "Candid Executive", "script_line": "Klien dan perusahaan sekarang tidak lagi terkesan dengan seberapa bagus hasil jadinya.", "visual_concept": "Klien eksekutif menatap presentasi di laptop dengan ekspresi datar tanpa ekspresi kagum", "search_query": "bored executive client looking unimpressed at design presentation meeting", "editor_note": "Klien tidak lagi terkesan pada hasil jadi."},
            {"file_name": "beat_07_20-25s_server_crisis_alert.jpg", "duration": "5s", "timestamp": "00:20 - 00:25", "shot_type": "High Pressure Tech", "script_line": "Mata uang baru di dunia kerja bukan lagi 'apa yang bisa Anda tunjukkan', melainkan 'seberapa bisa Anda dipercaya untuk bertanggung jawab saat sistem bermasalah'.", "visual_concept": "Insinyur senior tenang memimpin penanganan krisis sistem crash di ruang kontrol", "search_query": "calm engineer resolving critical system outage crisis control room leader", "editor_note": "Keberanian bertanggung jawab saat sistem bermasalah."},
            {"file_name": "beat_08_25-30s_authentic_handshake_deal.jpg", "duration": "5s", "timestamp": "00:25 - 00:30", "shot_type": "Close-Up Trust", "script_line": "Keberanian mengambil keputusan dan integritas rekam jejak personal adalah hal yang tidak bisa diprompt oleh bot.", "visual_concept": "Jabat tangan dua profesional dengan kontak mata tegas dan saling percaya", "search_query": "authentic firm handshake between two professionals trust integrity deal", "editor_note": "Integritas yang tidak bisa diprompt oleh bot."},
            {"file_name": "beat_09_30-36s_authentic_human_gaze.jpg", "duration": "6s", "timestamp": "00:30 - 00:36", "shot_type": "Direct Eye Contact", "script_line": "Pertanyaannya: kalau hasil karya teknis Anda bisa ditiru AI dalam lima detik, apa satu alasan klien harus tetap memilih Anda sebagai manusianya?", "visual_concept": "Potret wajah profesional menatap lurus ke kamera dengan raut berkarakter dan tenang", "search_query": "confident professional looking directly into camera authentic human gaze", "editor_note": "Tatapan langsung ke lensa kamera penonton. Fade out."}
        ]
    },
    {
        "id": "narasi-10",
        "title": "Alasan Sebenarnya Kenapa Pekerja Muda Mulai Kabur dari Jakarta",
        "pillar": "PROPERTY × FUTURE × HUMAN × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-10",
        "beats": [
            {"file_name": "beat_01_00-02s_taped_moving_box.jpg", "duration": "2s", "timestamp": "00:00 - 00:02", "shot_type": "Close-Up Action", "script_line": "Pernah perhatiin nggak...", "visual_concept": "Tangan melakban kardus cokelat bertuliskan 'PINDAH' di lantai apartemen", "search_query": "hands applying packing tape to cardboard moving box relocation apartment", "editor_note": "Cut pembuka melakban kardus pindahan."},
            {"file_name": "beat_02_02-05s_colleague_farewell_card.jpg", "duration": "3s", "timestamp": "00:02 - 00:05", "shot_type": "Office Still", "script_line": "...kenapa belakangan ini makin banyak teman kantor kita yang tiba-tiba pamit pindah tinggal ke luar kota atau pinggiran bukit?", "visual_concept": "Meja kantor yang sudah dikosongkan dengan cangkir selamat jalan dari rekan kerja", "search_query": "empty office desk farewell farewell card leaving colleague city transition", "editor_note": "Meja kantor yang dikosongkan."},
            {"file_name": "beat_03_05-09s_metropolitan_traffic_choke.jpg", "duration": "4s", "timestamp": "00:05 - 00:09", "shot_type": "Urban Nightmare", "script_line": "Secara hitungan lama, Jakarta dan kota megapolitan adalah pusat uang, pusat pergaulan, dan pusat karier tertinggi.", "visual_concept": "Kemacetan lalu lintas Jakarta di bawah flyover dengan ribuan motor dan mobil padat merayap", "search_query": "congested metropolitan city traffic jam exhaust smoke busy rush hour road", "editor_note": "Kemacetan parah kota megapolitan."},
            {"file_name": "beat_04_09-13s_misty_mountain_porch.jpg", "duration": "4s", "timestamp": "00:09 - 00:13", "shot_type": "Serene Vista", "script_line": "Tapi anehnya, orang-orang dengan penghasilan stabil justru memilih meninggalkan gemerlap kota besar dan beli tanah di tempat yang jauh lebih tenang.", "visual_concept": "Teras rumah kayu di lereng bukit dengan pemandangan lembah berkabut sejuk", "search_query": "wooden porch overlooking tranquil misty mountain hills terrace peaceful morning", "editor_note": "Kontras drastis: tanah tenang di pinggiran bukit."},
            {"file_name": "beat_05_13-17s_industrial_factory_smoke.jpg", "duration": "4s", "timestamp": "00:13 - 00:17", "shot_type": "Historical Archive", "script_line": "Kenapa bisa begitu? Karena revolusi industri dulu memaksa manusia berkerumun dekat pabrik dan gedung kantor demi mencari nafkah.", "visual_concept": "Cerobong asap pabrik era industri abad 19-20 dengan pekerja berjalan berkerumun", "search_query": "industrial revolution factory chimneys smoke historical workers walking urban factory", "editor_note": "Revolusi industri mengurung manusia dekat pabrik."},
            {"file_name": "beat_06_17-21s_remote_laptop_tea_estate.jpg", "duration": "4s", "timestamp": "00:17 - 00:21", "shot_type": "Modern Freedom", "script_line": "Tapi hari ini, ketika laptop dan sistem cloud memungkinkan kita bekerja dari mana saja, otak manusia mulai menuntut hak biologisnya kembali.", "visual_concept": "Laptop menyala di samping cangkir teh dengan latar belakang kebun teh hijau luas", "search_query": "laptop on wooden outdoor table overlooking green tea plantation mountain breeze", "editor_note": "Laptop bekerja dari teras kebun teh."},
            {"file_name": "beat_07_21-25s_concrete_box_claustrophobia.jpg", "duration": "4s", "timestamp": "00:21 - 00:25", "shot_type": "Brutalist Density", "script_line": "Manusia tidak pernah berevolusi untuk hidup di dalam kotak beton sempit, menghirup asap knalpot dua jam sehari, dan mendengar klakson macet.", "visual_concept": "Deretan balkon apartemen beton bertingkat rapat tanpa pohon satu pun", "search_query": "dense brutalist concrete apartment balconies crowded urban living cage", "editor_note": "Kotak beton sempit dan asap knalpot."},
            {"file_name": "beat_08_25-30s_barefoot_grass_morning.jpg", "duration": "5s", "timestamp": "00:25 - 00:30", "shot_type": "Tactile Biological", "script_line": "Begitu kerja jarak jauh membebaskan lokasi kita, orang-orang cerdas langsung menukar kemacetan dengan udara bersih dan pekarangan tanah nyata.", "visual_concept": "Kaki telanjang melangkah di rumput hijau berembun segar dengan pekarangan luas", "search_query": "barefoot feet walking on fresh green grass dew morning garden grounding", "editor_note": "Kaki telanjang menginjak rumput berembun pagi."},
            {"file_name": "beat_09_30-36s_mountain_horizon_escape.jpg", "duration": "6s", "timestamp": "00:30 - 00:36", "shot_type": "Open Freedom", "script_line": "Kalau pekerjaan Anda besok pagi bisa dikerjakan seratus persen dari mana saja, apakah Anda masih mau bertahan di tengah hiruk-pikuk macetnya kota besar?", "visual_concept": "Seseorang berdiri santai di teras rumah bukit menatap kebebasan lembah hijau luas", "search_query": "person standing casually on rural hilltop porch looking at vast green horizon freedom", "editor_note": "Menatap kebebasan alam tanpa macet. Fade out."}
        ]
    },
    {
        "id": "narasi-11",
        "title": "Dikelilingi 8 Miliar Manusia, tapi Curhatnya ke Bot AI",
        "pillar": "AI × HUMAN × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-11",
        "beats": [
            {"file_name": "beat_01_00-02s_typing_confession_dark.jpg", "duration": "2s", "timestamp": "00:00 - 00:02", "shot_type": "Extreme Close-Up", "script_line": "Ada satu fenomena yang kedengarannya sepele...", "visual_concept": "Jari mengetik kata-kata curhat rapuh di layar chat smartphone malam hari", "search_query": "close up typing emotional text message into chatbot app glowing screen dark", "editor_note": "Cut kilat 2 detik mengetik curhat di malam hari."},
            {"file_name": "beat_02_02-05s_creepy_ai_relationship.jpg", "duration": "3s", "timestamp": "00:02 - 00:05", "shot_type": "Moody Bed", "script_line": "...tapi bikin bulu kuduk berdiri: semakin hari, semakin banyak orang yang memilih curhat ke chatbot AI dibanding ke pasangannya sendiri.", "visual_concept": "Seseorang rebahan memeluk bantal sambil membaca balasan chatbot AI yang menenangkan", "search_query": "person lying in dark bedroom reading text message glow comforting chatbot", "editor_note": "Curhat ke bot dibanding pasangan sendiri."},
            {"file_name": "beat_03_05-09s_crowded_city_isolation.jpg", "duration": "4s", "timestamp": "00:05 - 00:09", "shot_type": "Blur Motion Crowd", "script_line": "Kita hidup di planet dengan delapan miliar manusia dan ribuan kontak di media sosial.", "visual_concept": "Lautan manusia melintasi zebra cross kota besar dengan motion blur cepat", "search_query": "blurred crowd of commuters crossing busy urban intersection eight billion people", "editor_note": "Lautan 8 miliar manusia di kota."},
            {"file_name": "beat_04_09-13s_solitary_text_bubble.jpg", "duration": "4s", "timestamp": "00:09 - 00:13", "shot_type": "Digital Empathy", "script_line": "Tapi anehnya, saat hati kita hancur atau pikiran lagi kalut, kita justru merasa paling aman mengetik curahan hati ke kotak teks algoritma di layar smartphone.", "visual_concept": "Gelembung pesan teks hijau menyala lembut di layar gelap dengan kata-kata penenang", "search_query": "glowing chat bubbles on smartphone screen comforting text message digital listener", "editor_note": "Kotak teks algoritma sebagai benteng aman."},
            {"file_name": "beat_05_13-17s_judgmental_world_noise.jpg", "duration": "4s", "timestamp": "00:13 - 00:17", "shot_type": "Social Strain", "script_line": "Kenapa kita melakukan itu? Jawabannya bukan karena AI itu pintar. Jawabannya karena manusia di sekitar kita seringkali terlalu sibuk, gampang menghakimi...", "visual_concept": "Wajah teman atau pasangan memalingkan muka asyik bermain HP sendiri di meja makan", "search_query": "couple sitting at dining table both ignoring each other staring at phones judgment", "editor_note": "Manusia sekitar sibuk dan menghakimi."},
            {"file_name": "beat_06_17-21s_tireless_ai_listener.jpg", "duration": "4s", "timestamp": "00:17 - 00:21", "shot_type": "Solitary Relief", "script_line": "...atau memotong omongan kita dengan nasihat sok tahu. AI memberikan apa yang langka di dunia nyata: pendengar setia yang tidak pernah capek dan tidak pernah menilai kita salah.", "visual_concept": "Seseorang mendekap ponsel di dada sambil menghela napas lega merasa didengarkan", "search_query": "tearful person holding glowing smartphone close to heart relief feeling heard", "editor_note": "Pendengar setia yang tidak pernah menilai salah."},
            {"file_name": "beat_07_21-25s_shattered_mirror_empathy.jpg", "duration": "4s", "timestamp": "00:21 - 00:25", "shot_type": "Psychological Horror", "script_line": "Tapi inilah bahayanya empati sintetis. AI memang bisa menenangkan kita di malam hari, tapi ia tidak punya detak jantung, tidak bisa memeluk, dan tidak pernah benar-benar peduli.", "visual_concept": "Bayangan wajah retak terdistorsi di permukaan cermin mekanik yang dingin", "search_query": "broken mirror reflection distorted sad human face synthetic cold reflection", "editor_note": "Bahaya empati sintetis: cermin mekanik."},
            {"file_name": "beat_08_25-29s_cold_mechanical_cage.jpg", "duration": "4s", "timestamp": "00:25 - 00:29", "shot_type": "Cold Tech Prison", "script_line": "Kita sedang mengobati kesepian manusia dengan cermin mekanik yang hanya memantulkan suara kita sendiri.", "visual_concept": "Siluet seseorang duduk memeluk lutut di ruangan dingin diterangi pendaran cahaya monitor", "search_query": "silhouette person sitting against wall in dark room illuminated by cold smartphone light", "editor_note": "Memantulkan suara kita sendiri di ruangan dingin."},
            {"file_name": "beat_09_29-35s_real_human_eye_connection.jpg", "duration": "6s", "timestamp": "00:29 - 00:35", "shot_type": "Warm Eye Contact", "script_line": "Kapan terakhir kali Anda duduk berdua dengan seseorang, menatap matanya, dan mendengar ceritanya tanpa ada HP di atas meja?", "visual_concept": "Dua orang sahabat duduk di kedai kopi hangat saling menatap mata dengan senyum tulus", "search_query": "two friends sitting together at coffee shop making eye contact genuine conversation laughing", "editor_note": "Menatap mata dan mendengar cerita tanpa HP di meja. Fade out."}
        ]
    },
    {
        "id": "narasi-12",
        "title": "Mengapa Rumah Orang Tua Seringkali Berubah Jadi Sunyi dan Sengketa?",
        "pillar": "PROPERTY × HUMAN × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-12",
        "beats": [
            {"file_name": "beat_01_00-03s_rusty_padlock_gate.jpg", "duration": "3s", "timestamp": "00:00 - 00:03", "shot_type": "Macro Neglect", "script_line": "Pernah nggak lewat di depan rumah tua keluarga...", "visual_concept": "Gembok besi berkarat mengunci pintu pagar besi rumah tua keluarga yang usang", "search_query": "rusty padlock on weathered iron gate abandoned overgrown family house", "editor_note": "Gembok berkarat di pagar rumah tua."},
            {"file_name": "beat_02_03-06s_overgrown_weeds_yard.jpg", "duration": "3s", "timestamp": "00:03 - 00:06", "shot_type": "Wide Decay", "script_line": "...yang dulu pas lebaran ramai banget oleh tawa anak-cucu, tapi sekarang pintunya digembok dan halamannya dipenuhi rumput liar?", "visual_concept": "Halaman rumah megah tua dipenuhi ilalang liar setinggi dada dan daun kering berserakan", "search_query": "overgrown wild grass weeds front yard of abandoned old colonial house decay", "editor_note": "Halaman penuh ilalang liar setinggi dada."},
            {"file_name": "beat_03_06-10s_vintage_banquet_laughter.jpg", "duration": "4s", "timestamp": "00:06 - 00:10", "shot_type": "Golden Memory", "script_line": "Orang tua kita dulu berjuang puluhan tahun, menahan lapar dan banting tulang, cuma demi satu mimpi: membangun rumah besar agar seluruh keluarga bisa berkumpul selamanya...", "visual_concept": "Foto kenangan masa lalu: keluarga besar tiga generasi tertawa bahagia makan bersama", "search_query": "warm nostalgic memory happy multigenerational family dinner banquet laughing vintage", "editor_note": "Tawa keluarga besar tiga generasi di masa lalu."},
            {"file_name": "beat_04_10-14s_for_sale_cloth_banner.jpg", "duration": "4s", "timestamp": "00:10 - 00:14", "shot_type": "Harsh Reality", "script_line": "...Tapi begitu orang tua tiada, rumah megah itu kerap jadi rebutan waris atau dijual murah karena nggak ada anak yang mau menempatinya.", "visual_concept": "Spanduk 'DIJUAL CEPAT / TANAH SENGKETA' terpasang miring di pagar rumah", "search_query": "for sale banner tied to gate of grand old house family dispute liquidation", "editor_note": "Spanduk Dijual Cepat / sengketa waris."},
            {"file_name": "beat_05_14-18s_empty_concrete_hall.jpg", "duration": "4s", "timestamp": "00:14 - 00:18", "shot_type": "Hollow Space", "script_line": "Kenapa realitas ini berulang di begitu banyak keluarga? Karena kita sering salah paham mengira bahwa yang membuat keluarga bersatu adalah sertifikat tanah dan dinding batanya...", "visual_concept": "Ruang tengah rumah kosong melompong dengan debu menari di berkas cahaya jendela", "search_query": "empty dusty spacious living room abandoned house sunbeam through window concrete", "editor_note": "Ruang kosong berdebu: dinding bata tak bisa merekatkan hati."},
            {"file_name": "beat_06_18-23s_welcoming_grandmother_smile.jpg", "duration": "5s", "timestamp": "00:18 - 00:23", "shot_type": "Soul of Home", "script_line": "Rumah fisik hanyalah wadah kosong. Jiwa pemersatunya bukan pada bangunannya, melainkan pada sosok yang menyambut di depan pintu.", "visual_concept": "Sosok ibu atau nenek tua tersenyum hangat dengan mata berkaca-kaca membuka pintu", "search_query": "loving elderly mother smiling welcoming warmly open front door embracing", "editor_note": "Ibu/nenek tua tersenyum menyambut di pintu, jiwa sejati rumah."},
            {"file_name": "beat_07_23-28s_frozen_cement_decay.jpg", "duration": "5s", "timestamp": "00:23 - 00:28", "shot_type": "Poetic Emptiness", "script_line": "Begitu sosok pemaaf itu tiada, rumah megah sekalipun langsung menyusut kembali menjadi tumpukan semen beku yang kehilangan maknanya.", "visual_concept": "Pintu kayu lapuk yang sedikit terbuka menampakkan lantai semen dingin tanpa jejak kaki", "search_query": "weathered wooden door open into empty abandoned dark room cold concrete sadness", "editor_note": "Tumpukan semen beku yang kehilangan maknanya."},
            {"file_name": "beat_08_28-35s_kissing_wrinkled_hand.jpg", "duration": "7s", "timestamp": "00:28 - 00:35", "shot_type": "Intimate Devotion", "script_line": "Bagi Anda yang orang tuanya masih ada hari ini: kapan terakhir kali Anda pulang ke rumah bukan untuk urusan uang, tapi cuma untuk mencium tangannya?", "visual_concept": "Anak mencium takzim punggung tangan tua orang tuanya yang berkerut dengan penuh rasa cinta", "search_query": "adult child lovingly kissing elderly parent wrinkled hands deep respect love tears", "editor_note": "Mencium punggung tangan tua orang tua dengan haru. Fade out."}
        ]
    }
]

def main():
    session_id = init_mcp_session()
    
    for plan in MICROBEATS_09_TO_12:
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
