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
            "clientInfo": {"name": "pexafy-microbeat-master-part2", "version": "1.0"}
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

MICROBEATS_04_TO_15 = [
    {
        "id": "narasi-04",
        "title": "Harga Nyata yang Kita Bayar untuk Otomasi 5 Detik",
        "pillar": "TECHNOLOGY × WORK × HUMAN × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-04",
        "beats": [
            {"file_name": "beat_01_00-02s_fast_thumb_scroll.jpg", "duration": "2s", "timestamp": "00:00 - 00:02", "shot_type": "Macro Motion", "script_line": "Cuma butuh lima detik...", "visual_concept": "Jari jempol scrolling sangat cepat di layar HP menyala biru", "search_query": "close up thumb rapidly scrolling on glowing smartphone screen blue light darkness", "editor_note": "Cut pembuka kilat 2s."},
            {"file_name": "beat_02_02-05s_document_summary_prompt.jpg", "duration": "3s", "timestamp": "00:02 - 00:05", "shot_type": "Screen POV", "script_line": "...buat AI bikin ringkasan dokumen 50 halaman. Tapi pernah nggak Anda hitung...", "visual_concept": "Dokumen tebal PDF diringkas kilat oleh software AI di laptop", "search_query": "software ai summarizing long text document screen digital interface", "editor_note": "Visual AI meringkas cepat."},
            {"file_name": "beat_03_05-08s_hidden_cost_shadow.jpg", "duration": "3s", "timestamp": "00:05 - 00:08", "shot_type": "Moody Still", "script_line": "...apa harga mahal yang diam-diam sedang kita bayar untuk kemudahan itu?", "visual_concept": "Wajah seseorang terpaku menatap ponsel dalam kegelapan", "search_query": "shadowy face of person staring deeply into glowing mobile screen solitude", "editor_note": "Visual misteri harga mahal tak kasat mata."},
            {"file_name": "beat_04_08-11s_rapid_information_flux.jpg", "duration": "3s", "timestamp": "00:08 - 00:11", "shot_type": "Abstract Tech", "script_line": "Kita merasa semakin cerdas karena bisa tahu intisari segala hal dalam hitungan detik.", "visual_concept": "Aliran data digital dan headline berita meluncur deras", "search_query": "fast moving digital information data stream abstract conceptual lights", "editor_note": "Sensasi serbuan informasi kilat."},
            {"file_name": "beat_05_11-15s_open_book_desk.jpg", "duration": "4s", "timestamp": "00:11 - 00:15", "shot_type": "Tabletop Still", "script_line": "Tapi anehnya, di saat yang sama, kemampuan kita untuk duduk tenang membaca satu bab buku...", "visual_concept": "Buku cetak terbuka di atas meja kayu di samping cangkir kopi yang tenang", "search_query": "open paper book resting on rustic wooden desk warm reading light", "editor_note": "Keheningan buku cetak fisik."},
            {"file_name": "beat_06_15-18s_buzzing_phone_distraction.jpg", "duration": "3s", "timestamp": "00:15 - 00:18", "shot_type": "Close-Up Rack Focus", "script_line": "...tanpa gelisah meraih HP justru hampir lenyap sama sekali.", "visual_concept": "Tangan gelisah terdorong meraih smartphone yang bergetar di samping buku", "search_query": "hand reaching for buzzing smartphone next to open paper book distraction", "editor_note": "Rack focus dari halaman buku ke tangan yang meraih HP."},
            {"file_name": "beat_07_18-22s_neuroscience_brain_mesh.jpg", "duration": "4s", "timestamp": "00:18 - 00:22", "shot_type": "Scientific Concept", "script_line": "Riset neurosains berulang kali membuktikan: otak manusia tidak membentuk wawasan mendalam dari kesimpulan instan.", "visual_concept": "Visualisasi neuron otak biologis dengan sinapsis listrik menyala", "search_query": "biological human brain neuron network glowing synaptic pathways science", "editor_note": "Visual riset otak biologis."},
            {"file_name": "beat_08_22-26s_slow_pencil_sketch.jpg", "duration": "4s", "timestamp": "00:22 - 00:26", "shot_type": "Macro Craft", "script_line": "Pemikiran kritis dan intuisi kreatif justru lahir saat otak kita berjuang mencerna detail yang rumit...", "visual_concept": "Goresan pensil menulis perlahan di atas kertas jurnal dengan coretan pemikiran", "search_query": "hand writing slowly with pencil in paper journal crossed out notes thinking", "editor_note": "Close up pensil bergulat di kertas."},
            {"file_name": "beat_09_26-30s_daydreaming_boredom.jpg", "duration": "4s", "timestamp": "00:26 - 00:30", "shot_type": "Contemplative Portrait", "script_line": "...merasakan kebosanan, dan menemukan polanya sendiri secara perlahan.", "visual_concept": "Seseorang duduk melamun di dekat jendela menikmati kebosanan dan hening", "search_query": "person sitting by window staring out daydreaming embracing quiet boredom", "editor_note": "Visual merasakan kebosanan positif."},
            {"file_name": "beat_10_30-34s_surrendering_thought_algorithm.jpg", "duration": "4s", "timestamp": "00:30 - 00:34", "shot_type": "Cold Tech Detail", "script_line": "Saat kita menyerahkan seluruh proses pergulatan berpikir itu ke algoritma, kita memang menghemat waktu di jam kerja.", "visual_concept": "Kursor prompt AI berkedip di monitor dengan kode otomatis terisi", "search_query": "ai prompt cursor blinking computer monitor automated workflow generation", "editor_note": "Visual otomatisasi pergulatan nalar."},
            {"file_name": "beat_11_34-39s_anxious_blue_face.jpg", "duration": "5s", "timestamp": "00:34 - 00:39", "shot_type": "Dramatic Close-Up", "script_line": "Tapi kita membayar kompensasinya dengan menukar ketajaman nalar biologis kita...", "visual_concept": "Wajah pemuda tampak cemas dan gelisah disinari cahaya dingin layar monitor", "search_query": "anxious face of person illuminated solely by blue screen light dark room", "editor_note": "Pencahayaan dramatis menonjolkan kecemasan nalar."},
            {"file_name": "beat_12_39-44s_mindless_metro_crowd.jpg", "duration": "5s", "timestamp": "00:39 - 00:44", "shot_type": "Social Commentary", "script_line": "...menjadi konsumen konten yang gampang cemas dan gampang disetir opini luar.", "visual_concept": "Kerumunan orang di stasiun kereta semuanya menunduk terpaku ke layar smartphone masing-masing", "search_query": "crowd of commuters on metro train all looking down at smartphones zombies", "editor_note": "Kerumunan orang terpaku layar, mudah disetir opini luar."},
            {"file_name": "beat_13_44-48s_turning_off_device.jpg", "duration": "4s", "timestamp": "00:44 - 00:48", "script_line": "Kapan terakhir kali Anda duduk melamun sepuluh menit penuh...", "visual_concept": "Tangan membalikkan layar HP ke bawah di atas meja kayu", "search_query": "hand placing smartphone face down on wooden table taking digital detox", "editor_note": "Gerakan tegas meletakkan HP tertelungkup."},
            {"file_name": "beat_14_48-53s_unplugged_nature_breathe.jpg", "duration": "5s", "timestamp": "00:48 - 00:53", "shot_type": "Peaceful Outdoor", "script_line": "...tanpa ada layar menyala di depan mata, dan membiarkan pikiran Anda bernapas sendiri?", "visual_concept": "Seseorang duduk tenang di bangku taman hijau menghirup napas dalam tanpa gadget", "search_query": "peaceful person sitting on park bench eyes closed breathing fresh green nature", "editor_note": "Pikiran bernapas di alam terbuka."},
            {"file_name": "beat_15_53-58s_quiet_open_sky.jpg", "duration": "5s", "timestamp": "00:53 - 00:58", "shot_type": "Zen Horizon", "script_line": "Menurut Anda gimana?", "visual_concept": "Pemandangan langit terbuka luas dengan dedaunan pohon bergoyang diterpa angin", "search_query": "open sky with gentle tree leaves swaying in wind serene tranquil horizon", "editor_note": "Visual hening langit dan angin di penutupan."}
        ]
    },
    {
        "id": "narasi-05",
        "title": "Kenapa Tanah Makin Mahal Justru Saat Dunia Makin Virtual?",
        "pillar": "FUTURE × PROPERTY × HUMAN × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-05",
        "beats": [
            {"file_name": "beat_01_00-03s_neon_vr_cyberspace.jpg", "duration": "3s", "timestamp": "00:00 - 00:03", "shot_type": "Cyber Close-Up", "script_line": "Pernah kepikiran nggak: kalau masa depan katanya ada di dunia digital, AI, dan metaverse...", "visual_concept": "Seseorang memakai kacamata VR futuristik dengan cahaya neon ungu-cyan", "search_query": "person wearing futuristic virtual reality headset glowing neon cyber lights", "editor_note": "Visual futuristik metaverse."},
            {"file_name": "beat_02_03-07s_billionaire_land_contrast.jpg", "duration": "4s", "timestamp": "00:03 - 00:07", "shot_type": "High Contrast Vista", "script_line": "...kenapa orang-orang paling kaya di industri teknologi justru berlomba-lomba beli ribuan hektar tanah fisik di dunia nyata?", "visual_concept": "Lanskap perkebunan hijau luas ribuan hektar di bawah langit biru bersih", "search_query": "vast sprawling green farmland ranch estate mountain landscape open sky", "editor_note": "Kontras tajam: dari neon VR ke ribuan hektar tanah hijau nyata."},
            {"file_name": "beat_03_07-11s_cloud_living_illusion.jpg", "duration": "4s", "timestamp": "00:07 - 00:11", "shot_type": "Digital Illusion", "script_line": "Di internet, mereka menyuruh kita hidup di layar, kerja lewat cloud, dan bersenang-senang di ruang virtual.", "visual_concept": "Pekerja terjebak di depan tumpukan layar monitor berpendar dingin", "search_query": "person working in dark room surrounded by multiple glowing screens cloud computing", "editor_note": "Ilusi hidup di cloud."},
            {"file_name": "beat_04_11-15s_pristine_river_forest.jpg", "duration": "4s", "timestamp": "00:11 - 00:15", "shot_type": "Pristine Nature", "script_line": "Tapi diam-diam, portofolio kekayaan mereka justru dilarikan ke aset paling kuno di muka bumi: tanah, air bersih, dan ruang terbuka hijau.", "visual_concept": "Aliran sungai air jernih mengalir di tengah hutan hijau yang asri", "search_query": "crystal clear fresh river water flowing through lush untouched green forest", "editor_note": "Aset purba: air bersih dan tanah hijau."},
            {"file_name": "beat_05_15-19s_economic_scarcity_rule.jpg", "duration": "4s", "timestamp": "00:15 - 00:19", "shot_type": "Economic Symbol", "script_line": "Kenapa begitu kontradiktif? Jawabannya ada pada hukum dasar ekonomi: kelangkaan.", "visual_concept": "Timbangan kuno emas dan batu alam di atas meja kayu", "search_query": "vintage brass balance scale weight measurement scarcity value concept", "editor_note": "Hukum dasar kelangkaan."},
            {"file_name": "beat_06_19-23s_infinite_copy_paste.jpg", "duration": "4s", "timestamp": "00:19 - 00:23", "shot_type": "Abstract Multiplicity", "script_line": "Di era AI, apa pun yang bersifat digital—mulai dari baris kode, artikel pintar, foto, sampai video realistis...", "visual_concept": "Ribuan baris kode digital dan gambar AI berganda tak terhingga", "search_query": "digital code duplication endless repeating matrix screen green blue", "editor_note": "Kemampuan menggandakan barang digital miliaran kali."},
            {"file_name": "beat_07_23-28s_zero_marginal_crash.jpg", "duration": "5s", "timestamp": "00:23 - 00:28", "shot_type": "Financial Gravity", "script_line": "...bisa digandakan sampai miliaran kali dengan biaya hampir nol rupiah. Semakin berlimpah sesuatu di dunia digital, nilainya akan semakin anjlok.", "visual_concept": "Grafik nilai digital jatuh bebas ke bawah", "search_query": "falling chart line economic value depreciation dropping down red arrows", "editor_note": "Kelimpahan digital membuat nilainya anjlok."},
            {"file_name": "beat_08_28-33s_hands_holding_dark_soil.jpg", "duration": "5s", "timestamp": "00:28 - 00:33", "shot_type": "Extreme Tactile Close-Up", "script_line": "Kebalikannya, ada satu hal di alam semesta ini yang nggak akan pernah bisa digandakan oleh server tercanggih mana pun...", "visual_concept": "Tangan menangkup tanah hitam gembur yang subur dengan butiran tanah jatuh perlahan", "search_query": "hands holding rich dark fertile earth soil organic texture tactile close up", "editor_note": "Tangan menggenggam tanah basah subur, simbol kelangkaan fisik sejati."},
            {"file_name": "beat_09_33-38s_sunlight_on_green_earth.jpg", "duration": "5s", "timestamp": "00:33 - 00:38", "shot_type": "Golden Rays", "script_line": "...sepetak tanah fisik di bawah sinar matahari.", "visual_concept": "Sinar matahari pagi keemasan menyapu padang rumput hijau yang basah oleh embun", "search_query": "golden morning sun rays shining down onto fresh green meadow grass dew", "editor_note": "Sinar matahari nyata di atas tanah fisik."},
            {"file_name": "beat_10_38-43s_synthetic_world_flood.jpg", "duration": "5s", "timestamp": "00:38 - 00:43", "shot_type": "Surreal Glitch", "script_line": "Ketika seluruh dunia dibanjiri kepalsuan buatan mesin...", "visual_concept": "Visual glitch digital dan deepfake buatan mesin yang memenuhi layar", "search_query": "digital glitch distortion screen noise artificial deepfake synthetic visual", "editor_note": "Banjir kepalsuan buatan mesin."},
            {"file_name": "beat_11_43-48s_peaceful_wooden_haven.jpg", "duration": "5s", "timestamp": "00:43 - 00:48", "script_line": "...keaslian alam nyata dan ketenangan ruang fisik mendadak berubah jadi barang paling mewah di bumi.",
            "visual_concept": "Rumah panggung kayu modern di tepi danau hutan yang tenang dan terisolasi dari bising", "search_query": "minimalist wooden cabin retreat nestled beside serene lake forest mountain nature", "editor_note": "Ketenangan ruang fisik adalah barang paling mewah."},
            {"file_name": "beat_12_48-53s_parent_child_field_walk.jpg", "duration": "5s", "timestamp": "00:48 - 00:53", "shot_type": "Emotive Silhouette", "script_line": "Di masa depan nanti saat kecerdasan bisa didownload gratis oleh siapa saja...", "visual_concept": "Ayah dan anak kecil melangkah santai di pematang kebun hijau", "search_query": "parent walking with child hand in hand in green countryside meadow afternoon", "editor_note": "Langkah generasi di atas tanah fisik."},
            {"file_name": "beat_13_53-58s_sacred_earth_legacy.jpg", "duration": "5s", "timestamp": "00:53 - 00:58", "shot_type": "Sunset Horizon", "script_line": "...menurut Anda apa satu hal nyata yang bakal jadi warisan paling berharga untuk anak cucu kita?", "visual_concept": "Siluet pohon tua rindang berdiri kokoh di atas bukit hijau saat matahari terbenam", "search_query": "ancient solitary oak tree standing on grassy hill sunset golden hour horizon", "editor_note": "Pohon tua di puncak bukit saat senja. Fade out perlahan."}
        ]
    }
]

def main():
    session_id = init_mcp_session()
    
    for plan in MICROBEATS_04_TO_15:
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
