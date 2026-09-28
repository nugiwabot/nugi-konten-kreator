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
            "clientInfo": {"name": "pexafy-microbeat-master", "version": "1.0"}
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

# Complete 15 Narasi Micro-Beats Plans (15-18 Beats Each, 2-5 Seconds Dynamic Rhythm)
MICROBEAT_PLANS = [
    {
        "id": "narasi-01",
        "title": "Mengapa AI Bikin Cepat, tapi Kita Justru Makin Capek?",
        "pillar": "AI × HUMAN × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-01",
        "beats": [
            {"file_name": "beat_01_00-02s_ecu_tired_eyes.jpg", "duration": "2s", "timestamp": "00:00 - 00:02", "shot_type": "Extreme Close-Up", "script_line": "Pernah sadar nggak...", "visual_concept": "Mata lelah memerah menatap pendaran layar laptop di ruang gelap", "search_query": "extreme close up tired red human eyes reflecting glowing computer screen darkness", "editor_note": "Cut kilat pembuka (2s) langsung menancapkan rasa lelah emosional audiens."},
            {"file_name": "beat_02_02-05s_pov_typing_screen.jpg", "duration": "3s", "timestamp": "00:02 - 00:05", "shot_type": "POV Screen", "script_line": "...kenapa semakin canggih AI yang kita pakai di kantor, jam kerja kita rasanya justru makin berantakan?", "visual_concept": "Sudut pandang orang mengetik di laptop dengan puluhan jendela software terbuka", "search_query": "first person pov typing on laptop keyboard glowing screen late night messy office", "editor_note": "Tampilkan sudut pandang orang pertama (POV) mengetik tanpa henti."},
            {"file_name": "beat_03_05-08s_macro_clock_motion.jpg", "duration": "3s", "timestamp": "00:05 - 00:08", "shot_type": "Macro Motion Blur", "script_line": "Secara logika, kalau mesin bisa ngerjain tugas dua jam...", "visual_concept": "Jarum jam dinding kantor berputar cepat dengan efek motion blur waktu berkejaran", "search_query": "macro close up office wall clock hands moving fast blurred motion passage of time", "editor_note": "Speed-ramp 1.2x jarum jam yang berkejaran memvisualisasikan waktu yang hilang."},
            {"file_name": "beat_04_08-11s_rapid_keyboard_fingers.jpg", "duration": "3s", "timestamp": "00:08 - 00:11", "shot_type": "Medium Action", "script_line": "...jadi dua menit, kita harusnya punya waktu luang lebih banyak buat istirahat.", "visual_concept": "Jemari mengetik sangat cepat di keyboard mekanik berkejaran dengan deadline", "search_query": "fast typing fingers on glowing mechanical keyboard speed motion urgent work", "editor_note": "Kontras cepat dari jam dinding ke jari yang mengetik terburu-buru."},
            {"file_name": "beat_05_11-15s_cold_coffee_desk.jpg", "duration": "4s", "timestamp": "00:11 - 00:15", "shot_type": "Over-The-Shoulder", "script_line": "Tapi survei terbaru minggu ini ke ribuan profesional justru bilang sebaliknya...", "visual_concept": "Gelas kopi dingin tak tersentuh di samping tumpukan map berkas kantor berantakan", "search_query": "half empty cold coffee mug sitting next to messy stacks of documents office desk", "editor_note": "Visual keheningan kopi dingin, menyiratkan tidak ada waktu luang untuk santai."},
            {"file_name": "beat_06_15-18s_head_in_hands_burnout.jpg", "duration": "3s", "timestamp": "00:15 - 00:18", "shot_type": "Side Profile Reaction", "script_line": "...mayoritas pekerja merasa jauh lebih lelah dibanding tahun lalu.", "visual_concept": "Pekerja menunduk menopang dahi dengan kedua tangan di atas meja kerja lelah fisik", "search_query": "side profile office worker head in hands overwhelmed exhausted sitting at desk", "editor_note": "Reaksi fisik kelelahan (burnout) saat Nugi menyebut 'jauh lebih lelah'."},
            {"file_name": "beat_07_18-21s_cold_corporate_facade.jpg", "duration": "3s", "timestamp": "00:18 - 00:21", "shot_type": "Low Angle Architecture", "script_line": "Kenapa bisa begitu? Karena dalam ekonomi modern...", "visual_concept": "Fasad gedung kaca pencakar langit korporat menjulang dingin di kala senja abu-abu", "search_query": "cold monolithic glass skyscraper corporate headquarters towering upward grey cloudy sky", "editor_note": "Low angle gedung pencakar langit megah dingin, simbol mesin ekonomi modern."},
            {"file_name": "beat_08_21-25s_notification_barrage.jpg", "duration": "4s", "timestamp": "00:21 - 00:25", "shot_type": "Close-Up Screen", "script_line": "...efisiensi nggak pernah dihadiahkan dalam bentuk waktu santai. Efisiensi selalu diisi ulang dengan tuntutan kuota yang berkali-kali lipat.", "visual_concept": "Layar smartphone dipenuhi serbuan puluhan notifikasi pesan dan email kerja masuk bersamaan", "search_query": "smartphone screen flooded with endless incoming notifications message alerts chaos", "editor_note": "Tampilan layar HP dibombardir deretan pop-up notifikasi tanpa jeda."},
            {"file_name": "beat_09_25-29s_mountain_of_paperwork.jpg", "duration": "4s", "timestamp": "00:25 - 00:29", "shot_type": "Medium Detail", "script_line": "Dulu bikin laporan butuh seminggu, sekarang bos minta lima laporan dalam sehari...", "visual_concept": "Tumpukan berkas laporan kertas tinggi menumpuk di depan laptop pekerja", "search_query": "massive tall pile of paperwork folders files blocking computer screen office desk", "editor_note": "Pan vertikal cepat dari bawah ke atas tumpukan dokumen yang tak masuk akal."},
            {"file_name": "beat_10_29-33s_demanding_manager_shadow.jpg", "duration": "4s", "timestamp": "00:29 - 00:33", "shot_type": "Candid Reaction", "script_line": "...alasannya sederhana: 'kan sekarang udah ada AI'.", "visual_concept": "Sosok bayangan manajer berdiri di samping meja karyawan menuntut hasil kilat", "search_query": "boss manager standing over stressed employee pointing at laptop demanding deadline", "editor_note": "Cut pas suara kutipan bos. Memperlihatkan tekanan hierarki kantor."},
            {"file_name": "beat_11_33-37s_ai_server_racks.jpg", "duration": "4s", "timestamp": "00:33 - 00:37", "shot_type": "Tech Atmosphere", "script_line": "Jadi masalah sebenarnya bukan AI yang mengambil alih hidup kita.", "visual_concept": "Deretan rak server komputasi data center berpendar lampu biru dalam ruangan dingin", "search_query": "rows of high tech computer server racks blinking blue lights cold data center", "editor_note": "B-roll server AI yang dingin, menggeser fokus dari 'mesin' ke 'manusia'."},
            {"file_name": "beat_12_37-41s_robotic_cog_human.jpg", "duration": "4s", "timestamp": "00:37 - 00:41", "shot_type": "Cinematic Wide", "script_line": "Masalahnya adalah kita yang tanpa sadar memperlakukan diri kita sendiri seperti mesin...", "visual_concept": "Pekerja korporat berjalan sendirian di lorong beton simetris layaknya roda gigi mesin", "search_query": "solitary business person walking through stark brutalist concrete hallway symmetry cold", "editor_note": "Visual simetris dingin lorong korporat, memperkuat narasi dehumanisasi."},
            {"file_name": "beat_13_41-46s_empty_subway_stare.jpg", "duration": "5s", "timestamp": "00:41 - 00:46", "shot_type": "Moody Still", "script_line": "...mengukur harga diri kita hanya dari seberapa cepat kita bisa berproduksi.", "visual_concept": "Pekerja duduk sendirian di bangku stasiun malam hari dengan tatapan kosong menatap lantai", "search_query": "exhausted commuter sitting alone on empty subway station bench late night thoughtful", "editor_note": "Hold 5 detik. Biarkan penonton merasakan kehampaan tolok ukur 'harga diri = produktivitas'."},
            {"file_name": "beat_14_46-50s_slow_closing_laptop.jpg", "duration": "4s", "timestamp": "00:46 - 00:50", "shot_type": "Close-Up Action", "script_line": "Kalau mesin memang diciptakan untuk bekerja tanpa henti...", "visual_concept": "Tangan menutup layar laptop secara perlahan, memutus aliran cahaya biru", "search_query": "hands slowly closing laptop screen lid dark room stepping away from work", "editor_note": "Gerakan lambat menutup laptop, simbol pemutusan siklus kerja paksa mesin."},
            {"file_name": "beat_15_50-55s_breath_of_fresh_air.jpg", "duration": "5s", "timestamp": "00:50 - 00:55", "shot_type": "Outdoor Silhouette", "script_line": "...bukankah yang membedakan kita sebagai manusia adalah keberanian untuk tahu kapan harus berhenti?", "visual_concept": "Seseorang berdiri di balkon menghadap angin senja menarik napas dalam dengan mata terpejam tenang", "search_query": "person standing on balcony breathing fresh air eyes closed peaceful dusk silhouette", "editor_note": "Siluet tenang di balkon senja, visualisasi biologis keberanian untuk berhenti."},
            {"file_name": "beat_16_55-60s_hot_tea_calm_evening.jpg", "duration": "5s", "timestamp": "00:55 - 01:00", "shot_type": "Warm Tabletop", "script_line": "Menurut Anda gimana?", "visual_concept": "Cangkir keramik teh hangat dengan uap mengepul di samping buku kertas tanpa ada gadget", "search_query": "steaming hot ceramic cup of tea on wooden table next to paper book no phone cozy", "editor_note": "Visual hangat dan damai di akhir video. Beri jeda hening sebelum video loop."}
        ]
    },
    {
        "id": "narasi-02",
        "title": "Di Balik Alasan Gen Z Lebih Memilih Ngontrak",
        "pillar": "PROPERTY × HUMAN × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-02",
        "beats": [
            {"file_name": "beat_01_00-03s_casual_young_renter.jpg", "duration": "3s", "timestamp": "00:00 - 00:03", "shot_type": "Medium Lifestyle", "script_line": "Banyak orang tua sering heran dan nanya...", "visual_concept": "Anak muda duduk santai bersila di lantai kamar kos minimalis dengan kaos santai", "search_query": "young adult sitting cross legged on floor in small cozy minimalist apartment room", "editor_note": "B-roll pembuka suasana kasual anak muda di kamar sewa minimalis."},
            {"file_name": "beat_02_03-06s_phone_scrolling_bed.jpg", "duration": "3s", "timestamp": "00:03 - 00:06", "shot_type": "Top-Down View", "script_line": "...'Kenapa sih anak muda sekarang kok kayaknya santai banget dan lebih milih ngontrak dibanding beli rumah?'", "visual_concept": "Tampak atas seseorang rebahan di ranjang sederhana menatap layar HP santai", "search_query": "top down view young person lying on simple bed looking at smartphone relaxed", "editor_note": "Visual gaya hidup sewa yang tampak 'santai' dari kacamata orang tua."},
            {"file_name": "beat_03_06-08s_iced_coffee_closeup.jpg", "duration": "2s", "timestamp": "00:06 - 00:08", "shot_type": "Extreme Close-Up", "script_line": "Banyak pengamat buru-buru menyimpulkan...", "visual_concept": "Gelas es kopi susu kekinian dengan tetesan embun dingin di atas meja kafe estetik", "search_query": "iced latte coffee in clear plastic cup with condensation on wooden cafe table", "editor_note": "Cut cepat 2 detik pada gelas kopi, simbol stigma 'boros kopi'."},
            {"file_name": "beat_04_08-12s_nomad_laptop_backpack.jpg", "duration": "4s", "timestamp": "00:08 - 00:12", "shot_type": "Lifestyle Action", "script_line": "...kalau Gen Z itu manja, boros kopi, atau terlalu cinta kebebasan nomaden.", "visual_concept": "Pemuda membawa tas ransel besar bekerja dengan laptop di kafe bergaya nomaden", "search_query": "digital nomad traveler with backpack working on laptop in busy modern cafe", "editor_note": "Visual gaya hidup nomaden yang sering disalahartikan sebagai pilihan bebas."},
            {"file_name": "beat_05_12-16s_property_price_graph.jpg", "duration": "4s", "timestamp": "00:12 - 00:16", "shot_type": "Data Visual", "script_line": "Tapi kalau kita buka data kenaikan harga tanah dibanding pertumbuhan gaji riil lima tahun terakhir...", "visual_concept": "Layar tablet menampilkan grafik garis harga properti melonjak tajam merah", "search_query": "financial chart graph showing soaring real estate prices on digital tablet screen", "editor_note": "Grafik tren kenaikan harga properti vs gaji, membongkar ilusi 'santai'."},
            {"file_name": "beat_06_16-19s_stressed_budget_calculator.jpg", "duration": "3s", "timestamp": "00:16 - 00:19", "shot_type": "Close-Up Hand", "script_line": "...ada sesuatu yang janggal di balik kesimpulan itu.", "visual_concept": "Tangan memegang kalkulator di samping slip gaji dan tagihan dengan gestur cemas", "search_query": "person holding calculator over bills and financial spreadsheet looking worried stressed", "editor_note": "Kontras keras: dari kopi santai ke perhitungan angka matematis yang mustahil."},
            {"file_name": "beat_07_19-23s_suburban_cluster_rows.jpg", "duration": "4s", "timestamp": "00:19 - 00:23", "shot_type": "Drone / High Angle", "script_line": "Kenyataannya, survei membuktikan mayoritas anak muda sebenarnya tetap mendambakan punya rumah sendiri.", "visual_concept": "Pemandangan udara deretan rumah kluster subsidi pinggiran kota yang rapat dan jauh", "search_query": "aerial view rows of modern suburban cluster houses identical roofs neighborhood", "editor_note": "Deretan rumah pinggiran kota yang diimpikan tapi semakin tak terjangkau."},
            {"file_name": "beat_08_23-28s_commuter_train_crowd.jpg", "duration": "5s", "timestamp": "00:23 - 00:28", "shot_type": "Candid Documentary", "script_line": "Tapi ketika harga rumah sederhana di pinggiran kota menuntut cicilan separuh gaji selama 25 tahun...", "visual_concept": "Lautan pekerja berdesakan di dalam gerbong kereta komuter malam hari", "search_query": "crowded commuter train carriage passengers packed standing tired after work", "editor_note": "Visual realitas komuter KRL 25 tahun: berdesakan tiap hari demi rumah pinggiran."},
            {"file_name": "beat_09_28-32s_tired_window_reflection.jpg", "duration": "4s", "timestamp": "00:28 - 00:32", "shot_type": "Poetic Reflection", "script_line": "...otak manusia secara alami menyalakan mekanisme pertahanan diri: merasionalisasi keadaan.", "visual_concept": "Wajah lelah anak muda memantul di kaca jendela kereta malam yang melaju cepat", "search_query": "weary face reflection in dark train window glass night commuter motion blur", "editor_note": "Refleksi kaca kereta, visualisasi proses psikologis 'merasionalisasi keadaan'."},
            {"file_name": "beat_10_32-36s_sour_grapes_defense.jpg", "duration": "4s", "timestamp": "00:32 - 00:36", "shot_type": "Moody Solitude", "script_line": "Dalam psikologi, ketika sebuah kebutuhan dasar terasa mustahil dijangkau oleh perhitungan matematika...", "visual_concept": "Seseorang duduk termenung di tangga darurat gedung menatap ponsel dengan raut pasrah", "search_query": "young person sitting alone on emergency staircase looking down thoughtful resigned", "editor_note": "Sosok menyendiri di tangga darurat, menggambarkan keputusasaan tersembunyi."},
            {"file_name": "beat_11_36-41s_laughing_mask_friends.jpg", "duration": "5s", "timestamp": "00:36 - 00:41", "shot_type": "Social Contrast", "script_line": "...orang akan menutupi rasa putus asanya dengan narasi gaya hidup: 'Ah, ngontrak lebih fleksibel kok.'", "visual_concept": "Sekelompok anak muda nongkrong tertawa di kafe seolah tidak ada beban finansial", "search_query": "group of young friends laughing drinking together in cafe masking anxiety", "editor_note": "Tawa di kafe, visualisasi narasi 'gaya hidup fleksibel' yang menutupi keputusasaan."},
            {"file_name": "beat_12_41-46s_ancient_cave_fire.jpg", "duration": "5s", "timestamp": "00:41 - 00:46", "shot_type": "Metaphorical Primal", "script_line": "Padahal di lubuk hati terdalam, manusia purba di dalam diri kita...", "visual_concept": "Siluet manusia di dekat api unggun hangat di dalam gua pelindung alami", "search_query": "silhouette of person near warm glowing campfire cave shelter primal sanctuary", "editor_note": "Visual metaforis manusia purba dan api unggun, simbol naluri shelter biologis."},
            {"file_name": "beat_13_46-51s_warm_bedroom_sanctuary.jpg", "duration": "5s", "timestamp": "00:46 - 00:51", "shot_type": "Warm Sanctuary", "script_line": "...tetap butuh sepetak ruang aman yang nggak bisa digusur siapa pun.", "visual_concept": "Kamar tidur hangat dengan selimut tebal dan lampu meja temaram yang damai", "search_query": "warm cozy bedroom interior safe haven soft ambient bedside lamp comfort", "editor_note": "Kamar tidur hangat, simbol 'ruang aman hakiki' yang dirindukan setiap manusia."},
            {"file_name": "beat_14_51-56s_packing_boxes_moving.jpg", "duration": "5s", "timestamp": "00:51 - 00:56", "shot_type": "Transient Detail", "script_line": "Menurut Anda, apakah generasi muda sekarang beneran menikmati hidup nomaden...", "visual_concept": "Tumpukan kardus pindahan sewa rumah yang harus dikemas berulang kali setiap tahun", "search_query": "stacked cardboard moving boxes tape packed room relocation transient living", "editor_note": "Kardus pindahan sewa, realitas melelahkan di balik narasi 'hidup nomaden'."},
            {"file_name": "beat_15_56-62s_key_on_wooden_table.jpg", "duration": "6s", "timestamp": "00:56 - 01:02", "shot_type": "Cinematic Still", "script_line": "...atau kita cuma sedang belajar menertawakan sesuatu yang nggak sanggup kita beli?", "visual_concept": "Kunci rumah kuningan tunggal tergeletak di atas meja kayu dengan pencahayaan dramatis", "search_query": "single vintage brass door key resting on rustic wooden table dramatic cinematic light", "editor_note": "Close up kunci rumah di atas meja kayu. Tahan hingga penutupan video."}
        ]
    },
    {
        "id": "narasi-03",
        "title": "Ilusi Ruko Kosong di Tengah Kota yang Bising",
        "pillar": "AI × PROPERTY × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-03",
        "beats": [
            {"file_name": "beat_01_00-03s_traffic_blur_street.jpg", "duration": "3s", "timestamp": "00:00 - 00:03", "shot_type": "Motion Blur", "script_line": "Coba perhatikan pas lagi jalan di tengah kota...", "visual_concept": "Kemacetan lalu lintas jalan raya kota besar dengan motion blur kendaraan melaju", "search_query": "fast moving urban city traffic motion blur busy crowded street downtown", "editor_note": "Pembuka dinamis 3s: kemacetan kota yang bising dan bergerak cepat."},
            {"file_name": "beat_02_03-06s_closed_dusty_shutters.jpg", "duration": "3s", "timestamp": "00:03 - 00:06", "shot_type": "Street Level Cut", "script_line": "...jalanan macet parah, orang lalu-lalang, tapi kenapa deretan ruko tiga lantai di pinggir jalan justru makin banyak yang kosong dan berdebu?", "visual_concept": "Deretan pintu rolling door besi ruko toko berdebu tertutup rapat di trotoar", "search_query": "closed dusty metal rolling door storefront empty retail building sidewalk", "editor_note": "Kontras tajam dari jalanan macet ke pintu toko besi yang mati berdebu."},
            {"file_name": "beat_03_06-09s_for_rent_banner_close.jpg", "duration": "3s", "timestamp": "00:06 - 00:09", "shot_type": "Macro Close-Up", "script_line": "Dulu, rumus emas bisnis itu cuma tiga...", "visual_concept": "Spanduk pudar bertuliskan 'DISEWA / DIJUAL' di kaca jendela toko kusam", "search_query": "for lease sign on dirty storefront window fading paint empty commercial retail", "editor_note": "Close up pada tulisan Disewa yang mulai luntur kusam."},
            {"file_name": "beat_04_09-13s_prime_protocol_road.jpg", "duration": "4s", "timestamp": "00:09 - 00:13", "shot_type": "Wide Angle Protocol", "script_line": "...lokasi, lokasi, dan lokasi di jalan protokol. Tapi hari ini, punya toko di pinggir jalan raya utama bukan lagi jaminan ramai pembeli.", "visual_concept": "Jalan protokol utama dengan gedung bertingkat namun toko bawahnya sepi", "search_query": "wide main avenue urban road protocol street commercial shops sidewalk empty", "editor_note": "Wide shot jalan protokol utama, membongkar mitos 'lokasi lokasi lokasi'."},
            {"file_name": "beat_05_13-17s_worried_owner_calculator.jpg", "duration": "4s", "timestamp": "00:13 - 00:17", "shot_type": "Psychological Detail", "script_line": "Justru sebaliknya: banyak pemilik ruko yang mulai kebingungan bayar bunga bank.", "visual_concept": "Pemilik properti paruh baya memijat dahi menatap lembar tagihan bank bulanan", "search_query": "worried middle aged business owner rubbing forehead looking at bank loan papers", "editor_note": "Visual ekspresi cemas pemilik ruko menatap beban cicilan bunga bank."},
            {"file_name": "beat_06_17-21s_speeding_courier_box.jpg", "duration": "4s", "timestamp": "00:17 - 00:21", "shot_type": "Dynamic Action", "script_line": "Apa yang sebenarnya terjadi? Sederhana: internet, logistik kurir, dan sistem automasi AI diam-diam telah memindahkan aliran darah ekonomi kita.", "visual_concept": "Kurir motor membelah kemacetan membawa tumpukan kardus paket belanja", "search_query": "motorcycle delivery courier speeding through traffic carrying parcels backpack cargo", "editor_note": "Speed cut kurir motor meliuk di aspal, visualisasi pergeseran 'aliran darah ekonomi'."},
            {"file_name": "beat_07_21-25s_smartphone_checkout_click.jpg", "duration": "4s", "timestamp": "00:21 - 00:25", "shot_type": "Close-Up Hand", "script_line": "Dulu, jalan aspal adalah tempat bertemunya penjual dan pembeli...", "visual_concept": "Jari menekan tombol 'Beli Sekarang' di aplikasi e-commerce layar smartphone", "search_query": "close up finger tapping buy now checkout button on mobile shopping app screen", "editor_note": "Close up tombol beli di smartphone: transaksi berpindah dari ruko ke layar 6 inci."},
            {"file_name": "beat_08_25-29s_massive_logistics_hub.jpg", "duration": "4s", "timestamp": "00:25 - 00:29", "shot_type": "High Bay Warehouse", "script_line": "...Sekarang, jalan raya cuma jadi jalur motor kurir mengantarkan barang yang dibeli lewat layar ponsel dari gudang murah di pinggiran kota.", "visual_concept": "Gudang raksasa pinggiran kota dengan ribuan tumpukan kardus palet tertata otomatis", "search_query": "massive modern distribution warehouse stacked cardboard pallets automated logistics", "editor_note": "Gudang logistik murah di pinggiran kota yang menggilas fungsi ruko pusat kota."},
            {"file_name": "beat_09_29-33s_dead_concrete_interior.jpg", "duration": "4s", "timestamp": "00:29 - 00:33", "shot_type": "Eerie Stillness", "script_line": "Artinya, fungsi ruang fisik kota sedang dipaksa berubah total.", "visual_concept": "Ruang kosong ruko bertembok semen polos dengan kabel menjuntai dan lantai kotor", "search_query": "empty bare concrete room abandoned retail space dusty floor hanging wires", "editor_note": "Keheningan mencekam di dalam ruko kosong tak berpenghuni."},
            {"file_name": "beat_10_33-37s_pure_transaction_dying.jpg", "duration": "4s", "timestamp": "00:33 - 00:37", "script_line": "Ruang beton yang cuma nawarin fungsi transaksi jual-beli biasa pelan-pelan akan mati.", "visual_concept": "Rak toko besi tua yang kosong melompong ditinggalkan", "search_query": "empty dusty metal store shelves retail liquidation abandoned supermarket aisle", "editor_note": "Rak toko kosong: fungsi transaksi fisik konvensional telah mati."},
            {"file_name": "beat_11_37-42s_artisan_coffee_pour.jpg", "duration": "5s", "timestamp": "00:37 - 00:42", "shot_type": "Sensory Warmth", "script_line": "Yang bertahan cuma ruang fisik yang menawarkan apa yang nggak bisa dikirim kurir...", "visual_concept": "Barista menuangkan seduhan kopi filter manual dengan uap aroma wangi menguar", "search_query": "barista pouring manual brew filter coffee slow motion steam aroma cafe craft", "editor_note": "Slow-motion uap kopi: apa yang tidak bisa dikirim lewat kurir adalah 'pengalaman indra'."},
            {"file_name": "beat_12_42-47s_face_to_face_laugh.jpg", "duration": "5s", "timestamp": "00:42 - 00:47", "shot_type": "Human Connection", "script_line": "...pengalaman indra manusia, keheningan, dan perjumpaan tatap muka nyata.", "visual_concept": "Dua orang tertawa lepas saling menatap hangat saat berbincang di kafe yang nyaman", "search_query": "two people laughing warmly sitting together across table genuine human interaction", "editor_note": "Kehangatan tatap muka manusia yang tidak bisa digantikan oleh algoritma kurir."},
            {"file_name": "beat_13_47-52s_dusk_city_transformation.jpg", "duration": "5s", "timestamp": "00:47 - 00:52", "shot_type": "Dusk Metropolis", "script_line": "Kalau semua transaksi belanja pindah ke algoritma cloud...", "visual_concept": "Pemandangan senja kota dengan lampu neon toko berpadu dengan gedung perkantoran", "search_query": "dusk twilight skyline city buildings streetlights glowing blue orange hour", "editor_note": "Senja dramatis kota metropolis, transisi ke pertanyaan masa depan."},
            {"file_name": "beat_14_52-58s_abandoned_facade_reflection.jpg", "duration": "6s", "timestamp": "00:52 - 00:58", "shot_type": "Reflective Ending", "script_line": "...kira-kira sepuluh tahun lagi gedung-gedung ruko di tengah kota kita bakal berubah jadi apa ya?", "visual_concept": "Seseorang menatap pantulan dirinya di kaca ruko kosong di kala malam mulai turun", "search_query": "person looking at reflection in dark empty shop window glass night street mystery", "editor_note": "Refleksi bayangan di kaca toko kosong di malam hari. Fade out perlahan."}
        ]
    }
]

def main():
    session_id = init_mcp_session()
    
    for plan in MICROBEAT_PLANS:
        narasi_id = plan["id"]
        narasi_title = plan["title"]
        assets_dir = os.path.join(plan["folder"], "assets")
        os.makedirs(assets_dir, exist_ok=True)
        
        print(f"\n=======================================================")
        print(f"EXPANDING MICRO-BEATS: {narasi_id} ({len(plan['beats'])} dynamic cuts)")
        print(f"Target folder: {assets_dir}")
        print(f"=======================================================")
        
        downloaded_assets = []
        
        for idx, beat in enumerate(plan["beats"]):
            file_name = beat["file_name"]
            target_path = os.path.join(assets_dir, file_name)
            
            # If already downloaded and valid, skip download
            if os.path.exists(target_path) and os.path.getsize(target_path) > 10000:
                print(f"[{idx+1}/{len(plan['beats'])}] Already downloaded: {file_name}")
                downloaded_assets.append(beat)
                continue
                
            query = beat["search_query"]
            shot_type = beat.get("shot_type", "Visual Cut")
            duration = beat.get("duration", "3s")
            print(f"\n[{idx+1}/{len(plan['beats'])}] [{duration} | {shot_type}] Searching: '{query}'...")
            
            try:
                results = search_photos(session_id, query, orientation="portrait")
                if not results:
                    print(f"  Fallback broader search...")
                    results = search_photos(session_id, query[:45], orientation="portrait")
                
                if results:
                    chosen = results[0]
                    urls = chosen.get("urls", {})
                    img_url = urls.get("large") or urls.get("regular") or urls.get("full") or chosen.get("image_url")
                    
                    size_bytes = download_image(img_url, target_path)
                    print(f"  Saved {file_name} ({size_bytes:,} bytes)")
                    
                    beat_info = dict(beat)
                    beat_info["photo_id"] = chosen.get("photo_id")
                    beat_info["photographer"] = chosen.get("photographer_username") or chosen.get("photographer") or "Pexels Creator"
                    beat_info["source"] = chosen.get("source", "Pexels")
                    beat_info["source_url"] = chosen.get("source_image_url") or chosen.get("image_url")
                    downloaded_assets.append(beat_info)
                else:
                    print(f"  Warning: No image found for {file_name}")
            except Exception as e:
                print(f"  Error downloading beat {file_name}: {e}")
            
            time.sleep(0.3)
            
        # Write DYNAMIC MICROBEAT STORYBOARD to SCRIPT_AND_STORYBOARD.md
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
