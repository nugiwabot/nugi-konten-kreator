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
            "clientInfo": {"name": "pexafy-microbeat-master-part5", "version": "1.0"}
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

MICROBEATS_13_TO_15 = [
    {
        "id": "narasi-13",
        "title": "Mengapa Makin Banyak Scrolling Video Pendek, Jiwa Kita Makin Kosong?",
        "pillar": "TECHNOLOGY × HUMAN × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-13",
        "beats": [
            {"file_name": "beat_01_00-02s_lying_bed_scroll.jpg", "duration": "2s", "timestamp": "00:00 - 00:02", "shot_type": "Close-Up Bed", "script_line": "Pernah nggak, rebahan niatnya cuma mau refreshing lima menit...", "visual_concept": "Rebahan di kasur gelap memegang HP scrolling dengan tatapan mata mati rasa", "search_query": "person lying in messy bed dark room holding smartphone scrolling tired eyes", "editor_note": "Cut pembuka kilat 2 detik rebahan scrolling."},
            {"file_name": "beat_02_02-06s_numb_body_empty_mind.jpg", "duration": "4s", "timestamp": "00:02 - 00:06", "shot_type": "Physical Stiff", "script_line": "...scrolling video, tapi pas bangun satu jam kemudian badan malah rasanya makin pegal dan otak makin hampa?", "visual_concept": "Seseorang bangun dari kasur dengan leher pegal dan tatapan linglung hampa", "search_query": "person waking up from bed neck pain fatigue staring blankly exhausted", "editor_note": "Badan pegal dan otak hampa setelah 1 jam scrolling."},
            {"file_name": "beat_03_06-09s_entertaining_screen_flash.jpg", "duration": "3s", "timestamp": "00:06 - 00:09", "shot_type": "Visual Reflex", "script_line": "Secara teori, kita sedang menonton konten hiburan yang lucu, informatif, dan seru.", "visual_concept": "Kilatan warna-warni video pendek terpantul di kacamata atau bola mata", "search_query": "colorful vibrant video clips light reflections on glasses screen glare", "editor_note": "Layar warna-warni memantul cepat."},
            {"file_name": "beat_04_09-13s_strange_inner_anxiety.jpg", "duration": "4s", "timestamp": "00:09 - 00:13", "shot_type": "Chest Tightness", "script_line": "Tapi kenapa setelah ratusan video lewat di layar, perasaan yang tertinggal di dalam dada bukan rasa puas, melainkan rasa gelisah yang aneh?", "visual_concept": "Tangan memegang dada merasakan kegelisahan hampa yang aneh", "search_query": "hand clutching chest feeling strange anxiety restlessness alone in room", "editor_note": "Rasa gelisah yang aneh di dalam dada."},
            {"file_name": "beat_05_13-17s_story_arc_evolution.jpg", "duration": "4s", "timestamp": "00:13 - 00:17", "shot_type": "Classic Story", "script_line": "Otak biologis manusia berevolusi untuk memproses cerita yang utuh: ada awal, ada perjuangan di tengah, dan ada penyelesaian di akhir.", "visual_concept": "Ilustrasi bab buku novel dengan perjalanan awal, tengah, dan akhir", "search_query": "ancient storytelling around fire open classic novel chapters narrative", "editor_note": "Evolusi otak manusia memproses cerita utuh."},
            {"file_name": "beat_06_17-21s_ten_second_fake_climax.jpg", "duration": "4s", "timestamp": "00:17 - 00:21", "shot_type": "Glitch Rush", "script_line": "Tapi algoritma video pendek menyuntikkan klimaks instan setiap sepuluh detik tanpa memberi jeda bagi otak untuk mencerna makna.", "visual_concept": "Layar smartphone dengan angka timer 15 detik berkedip cepat memicu dopamine spike", "search_query": "rapid digital cuts smartphone timer fast dopamine video barrage", "editor_note": "Klimaks instan tiap sepuluh detik tanpa jeda."},
            {"file_name": "beat_07_21-25s_dopamine_burnout_neurons.jpg", "duration": "4s", "timestamp": "00:21 - 00:25", "shot_type": "Neuroscience Art", "script_line": "Akibatnya, reseptor dopamin kita mengalami kebas karena over-stimulasi.", "visual_concept": "Visualisasi sel saraf neuron otak yang terbakar dan kebas karena kelebihan dopamin", "search_query": "exhausted brain neurons fading dopamine receptors desensitization overload", "editor_note": "Reseptor dopamin mengalami kebas."},
            {"file_name": "beat_08_25-29s_fragmented_emotions_wall.jpg", "duration": "4s", "timestamp": "00:25 - 00:29", "shot_type": "Moody Slump", "script_line": "Otak kita kelelahan bukan karena berpikir keras, melainkan karena dibombardir serpihan emosi yang putus-putus tanpa pernah terhubung menjadi pemahaman yang utuh.", "visual_concept": "Seseorang duduk bersandar di lantai menatap dinding kosong dengan rasa hampa", "search_query": "person sitting on floor against wall staring blankly emotional depletion", "editor_note": "Duduk bersandar dinding, visualisasi serpihan emosi yang putus-putus."},
            {"file_name": "beat_09_29-35s_real_nature_balcony.jpg", "duration": "6s", "timestamp": "00:29 - 00:35", "shot_type": "Balcony Dusk", "script_line": "Kapan terakhir kali Anda mematikan layar, menaruh HP di ruangan lain, dan membiarkan mata Anda menikmati pemandangan nyata di sekitar Anda?", "visual_concept": "Seseorang berdiri santai di balkon menikmati pemandangan senja langit nyata tanpa memegang HP", "search_query": "person standing peacefully on balcony enjoying twilight evening sky no gadgets", "editor_note": "Menikmati pemandangan senja nyata tanpa gawai. Fade out."}
        ]
    },
    {
        "id": "narasi-14",
        "title": "Akhir dari Era Gedung Kantor Pencakar Langit",
        "pillar": "AI × PROPERTY × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-14",
        "beats": [
            {"file_name": "beat_01_00-03s_cbd_glass_tower_up.jpg", "duration": "3s", "timestamp": "00:00 - 00:03", "shot_type": "Low Angle Architecture", "script_line": "Pernah perhatiin gedung-gedung kaca pencakar langit di kawasan bisnis pusat kota?", "visual_concept": "Menara kaca pencakar langit menjulang tinggi berkilau di kawasan CBD", "search_query": "majestic glass skyscraper tower looking up commercial central business district", "editor_note": "Low angle megah gedung pencakar langit CBD."},
            {"file_name": "beat_02_03-06s_empty_desks_daylight.jpg", "duration": "3s", "timestamp": "00:03 - 00:06", "shot_type": "Interior Still", "script_line": "...Megah, berkilau di malam hari, tapi di jam kerja ruangannya banyak yang sepi melompong.", "visual_concept": "Lantai kantor korporat modern yang luas dengan deretan kubikel kosong di siang bolong", "search_query": "empty modern office floor vacant desk cubicles chairs quiet daylight", "editor_note": "Lantai kantor sepi melompong di jam kerja."},
            {"file_name": "beat_03_06-10s_billions_rent_waste.jpg", "duration": "4s", "timestamp": "00:06 - 00:10", "shot_type": "Financial Gravity", "script_line": "Perusahaan multinasional rela membayar sewa miliaran rupiah per lantai tiap tahunnya. Tapi anehnya, survei kehadiran karyawan menunjukkan rata-rata meja kantor modern cuma terisi empat puluh persen dari kapasitasnya.", "visual_concept": "Dokumen kontrak sewa gedung kantor mahal dengan barisan stempel korporat", "search_query": "commercial real estate lease agreement paperwork corporate office contract", "editor_note": "Sewa miliaran rupiah per lantai tapi hanya terisi 40%."},
            {"file_name": "beat_04_10-14s_vintage_typing_pool.jpg", "duration": "4s", "timestamp": "00:10 - 00:14", "shot_type": "Black & White Archive", "script_line": "Kenapa bisa begitu? Karena konsep gedung kantor bertingkat diciptakan pada abad ke-20 sebagai pabrik administrasi...", "visual_concept": "Foto hitam putih puluhan pegawai kantor abad 20 duduk berjejer rapi di meja mesin tik", "search_query": "vintage black and white typing pool office workers in rows 20th century factory style", "editor_note": "Pabrik administrasi abad ke-20."},
            {"file_name": "beat_05_14-18s_manager_policing_cubicles.jpg", "duration": "4s", "timestamp": "00:14 - 00:18", "shot_type": "Cubicle Pan", "script_line": "...atasan butuh melihat bawahan duduk rapi di kubikel biar yakin mereka bekerja.", "visual_concept": "Deretan kubikel kantor abu-abu yang kaku dan monoton", "search_query": "row of gray office cubicles partitions sterile corporate working environment", "editor_note": "Duduk rapi di kubikel abu-abu kaku."},
            {"file_name": "beat_06_18-22s_ai_agent_pipeline_screen.jpg", "duration": "4s", "timestamp": "00:18 - 00:22", "shot_type": "Modern Tech", "script_line": "Tapi di era sekarang, ketika agen AI dan software kolaborasi menangani tugas teknis secara otomatis, kehadiran fisik di meja kantor kehilangan maknanya.", "visual_concept": "Dashboard software AI agen memproses alur kerja otomatis di monitor ramping", "search_query": "sleek software dashboard automated workflow analytics glowing screen ai agents", "editor_note": "Agen AI menangani tugas teknis secara otomatis."},
            {"file_name": "beat_07_22-26s_wasted_commute_traffic.jpg", "duration": "4s", "timestamp": "00:22 - 00:26", "shot_type": "Commute Waste", "script_line": "Memaksa manusia terjebak macet dua jam di jalanan cuma buat duduk membuka laptop di gedung bertingkat adalah pemborosan energi peradaban yang konyol.", "visual_concept": "Pekerja terjebak di dalam mobil atau bus dalam kemacetan panjang menatap jam tangan", "search_query": "exhausted commuter stuck in traffic jam looking at wristwatch wasted time", "editor_note": "Macet 2 jam cuma buat buka laptop: pemborosan konyol."},
            {"file_name": "beat_08_26-30s_creative_collaboration_board.jpg", "duration": "4s", "timestamp": "00:26 - 00:30", "shot_type": "Collaborative Warmth", "script_line": "Gedung kantor di masa depan bukan lagi tempat mengerjakan tugas rutin, melainkan tempat berkumpul untuk diskusi ide besar yang butuh tatap muka.", "visual_concept": "Tim kreatif berdiri santai mengitari papan tulis bertukar gagasan besar penuh senyum", "search_query": "creative team collaborating standing around whiteboard sketching big ideas smiling", "editor_note": "Kantor masa depan: tempat kumpul diskusi ide besar."},
            {"file_name": "beat_09_30-36s_future_work_skyline.jpg", "duration": "6s", "timestamp": "00:30 - 00:36", "shot_type": "Rooftop Reflection", "script_line": "Kalau tugas Anda bisa dikerjakan di mana saja dengan bantuan AI, menurut Anda apa fungsi utama dari sebuah kantor fisik sepuluh tahun ke depan?", "visual_concept": "Seseorang berdiri di teras rooftop gedung menatap cakrawala kota saat senja keemasan", "search_query": "architect standing on rooftop garden terrace overlooking modern city sunset horizon", "editor_note": "Fungsi utama kantor fisik 10 tahun ke depan. Fade out."}
        ]
    },
    {
        "id": "narasi-15",
        "title": "Di Era AI Bisa Segalanya, Apa yang Membuat Manusia Tetap Bernilai?",
        "pillar": "FUTURE × HUMAN × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-15",
        "beats": [
            {"file_name": "beat_01_00-03s_holographic_ai_mesh.jpg", "duration": "3s", "timestamp": "00:00 - 00:03", "shot_type": "Futuristic AI", "script_line": "Ketika AI sekarang bisa nulis esai dalam sedetik, bikin program rumit, sampai mendiagnosis penyakit lebih cepat dari dokter biasa...", "visual_concept": "Visualisasi otak AI holografis dengan aliran data saraf kecerdasan buatan", "search_query": "futuristic artificial intelligence neural network data stream holographic brain", "editor_note": "Visual futuristik AI mengerjakan segalanya."},
            {"file_name": "beat_02_03-07s_existential_worker_shadow.jpg", "duration": "4s", "timestamp": "00:03 - 00:07", "shot_type": "Moody Shadow", "script_line": "...pernah nggak Anda bertanya: lalu apa gunanya kita sebagai manusia?", "visual_concept": "Sosok pekerja duduk termenung di ruang kerja gelap menatap bayangan dirinya", "search_query": "silhouette person sitting in dark office room existential crisis questioning worth", "editor_note": "Lalu apa gunanya kita sebagai manusia?"},
            {"file_name": "beat_03_07-11s_technical_skill_pedestal.jpg", "duration": "4s", "timestamp": "00:07 - 00:11", "shot_type": "Antique Metaphor", "script_line": "Pertanyaan ini bikin jutaan orang cemas dan gamang. Selama ratusan tahun, kita diajarkan bahwa nilai harga diri seseorang ditentukan oleh keahlian teknis yang ia miliki...", "visual_concept": "Mesin hitung mekanik kuno atau kalkulator tua di atas meja kerja", "search_query": "vintage mechanical calculating machine ledger books technical skills past", "editor_note": "Harga diri ditentukan keahlian teknis."},
            {"file_name": "beat_04_11-15s_machine_perfect_calculation.jpg", "duration": "4s", "timestamp": "00:11 - 00:15", "shot_type": "Data Flow", "script_line": "...seberapa jago berhitung, seberapa pintar menghafal, atau seberapa cepat menganalisis data. Tapi ketika mesin terbukti bisa melakukan semua kemampuan kalkulasi itu jauh lebih sempurna dibanding otak kita...", "visual_concept": "Layar monitor memproses jutaan kalkulasi angka dalam hitungan milidetik", "search_query": "matrix of numbers calculations moving fast on modern screen perfection", "editor_note": "Kalkulasi mesin yang sempurna tanpa salah."},
            {"file_name": "beat_05_15-19s_golden_dawn_hope.jpg", "duration": "4s", "timestamp": "00:15 - 00:19", "shot_type": "Golden Horizon", "script_line": "...banyak orang merasa eksistensi dirinya mendadak terancam. Padahal kalau kita renungkan lebih dalam, krisis ini justru adalah kabar baik bagi peradaban.", "visual_concept": "Fajar matahari keemasan memecah kegelapan awan mendung di atas bumi", "search_query": "warm golden sunrise breaking through dark clouds symbol of hope new dawn", "editor_note": "Fajar harapan baru bagi peradaban."},
            {"file_name": "beat_06_19-23s_freed_from_calculator_myth.jpg", "duration": "4s", "timestamp": "00:19 - 00:23", "shot_type": "Liberation Metaphor", "script_line": "AI membebaskan kita dari ilusi bahwa manusia adalah mesin kalkulator biologis. Nilai tertinggi manusia tidak pernah terletak pada seberapa cepat kita mengolah data.", "visual_concept": "Seseorang melepas kacamata dan menarik napas lega memandang langit bebas", "search_query": "person taking off glasses looking up at bright sky feeling free from burden", "editor_note": "Bebas dari ilusi bahwa manusia adalah mesin kalkulator biologis."},
            {"file_name": "beat_07_23-28s_holding_hands_comfort.jpg", "duration": "5s", "timestamp": "00:23 - 00:28", "shot_type": "Tactile Empathy", "script_line": "Nilai sejati manusia terletak pada keberanian mengambil tanggung jawab moral, kemampuan berempati menatap penderitaan sesama...", "visual_concept": "Dua tangan saling menggenggam erat penuh kehangatan dan empati menenangkan", "search_query": "compassionate caring person holding hands supporting comfort empathy love", "editor_note": "Tangan menggenggam hangat: empati menatap penderitaan sesama."},
            {"file_name": "beat_08_28-33s_warm_embrace_unconditional.jpg", "duration": "5s", "timestamp": "00:28 - 00:33", "shot_type": "Unconditional Love", "script_line": "...dan cinta kasih tulus yang menolak digantikan oleh baris kode apa pun.", "visual_concept": "Pelukan tulus dua insan manusia dengan senyum penuh kasih tanpa syarat", "search_query": "genuine warm embrace hug between two people true human love tears of joy", "editor_note": "Cinta kasih tulus yang menolak digantikan baris kode."},
            {"file_name": "beat_09_33-40s_expressive_human_iris.jpg", "duration": "7s", "timestamp": "00:33 - 00:40", "shot_type": "Extreme Macro Soul", "script_line": "Di dunia yang semakin serba otomatis dan cerdas, satu sifat kemanusiaan apa di dalam diri Anda yang paling Anda jaga agar tidak pernah pudar?", "visual_concept": "Extreme close-up bola mata manusia memancarkan kilau jiwa yang hidup dan dalam", "search_query": "extreme close up human iris eye reflection of light authentic soul depth", "editor_note": "Extreme close up iris mata manusia. Fade out perlahan."}
        ]
    }
]

def main():
    session_id = init_mcp_session()
    
    for plan in MICROBEATS_13_TO_15:
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
