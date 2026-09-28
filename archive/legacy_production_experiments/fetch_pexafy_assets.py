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
            "clientInfo": {"name": "pexafy-narasi-downloader", "version": "1.0"}
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

NARASI_PLANS = [
    {
        "id": "narasi-01",
        "title": "Mengapa AI Bikin Cepat, tapi Kita Justru Makin Capek?",
        "pillar": "AI × HUMAN × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-01",
        "scenes": [
            {
                "file_name": "01_hook_overworked_laptop.jpg",
                "timestamp": "[00:00 - 00:05] HOOK",
                "script_line": "Pernah sadar nggak, kenapa semakin canggih AI yang kita pakai di kantor, jam kerja kita rasanya justru makin berantakan?",
                "visual_concept": "Pekerja kantor kelelahan di depan layar laptop malam hari dalam ruangan gelap",
                "search_query": "exhausted office worker staring at glowing laptop screen late night dark room tired overwhelmed",
                "b_roll_cue": "Cut dari talking-head Nugi saat menyebut 'jam kerja makin berantakan'. Gunakan slow digital zoom-in 110% untuk menonjolkan kelelahan emosional."
            },
            {
                "file_name": "02_tension_clock_overtime.jpg",
                "timestamp": "[00:05 - 00:18] TENSION & PARADOX",
                "script_line": "Secara logika, kalau mesin bisa ngerjain tugas dua jam jadi dua menit, kita harusnya punya waktu luang lebih banyak buat istirahat...",
                "visual_concept": "Jam dinding kantor berputar cepat dengan efek motion blur, tekanan waktu yang berlari",
                "search_query": "fast ticking wall clock passing time deadline hurry stress blurred office motion",
                "b_roll_cue": "Overlay b-roll jam / waktu berlari dengan speed-ramp tipis 1.2x saat membahas paradoks dua jam jadi dua menit."
            },
            {
                "file_name": "03_data_multitasking_screens.jpg",
                "timestamp": "[00:18 - 00:29] CONTEXT & THE REAL DATA (Part 1)",
                "script_line": "Kenapa bisa begitu? Karena dalam ekonomi modern, efisiensi nggak pernah dihadiahkan dalam bentuk waktu santai. Efisiensi selalu diisi ulang dengan tuntutan kuota yang berkali-kali lipat...",
                "visual_concept": "Meja kerja berantakan dengan banyak monitor, puluhan tab terbuka, dan tumpukan laporan",
                "search_query": "overwhelmed employee multiple computer screens charts open tabs cluttered work desk",
                "b_roll_cue": "Pan vertikal cepat dari bawah ke atas menampilkan rimba layar dan grafik pekerjaan yang menumpuk."
            },
            {
                "file_name": "04_data_five_reports_pressure.jpg",
                "timestamp": "[00:29 - 00:40] CONTEXT & THE REAL DATA (Part 2)",
                "script_line": "Dulu bikin laporan butuh seminggu, sekarang bos minta lima laporan dalam sehari, alasannya sederhana: 'kan sekarang udah ada AI'.",
                "visual_concept": "Profesional memegang kepala karena sakit kepala dan tekanan deadline korporat",
                "search_query": "stressed manager employee holding head in hands pressure demanding corporate office",
                "b_roll_cue": "Cut pas suara kutipan bos 'kan sekarang udah ada AI'. Tampilkan frustrasi nyata pekerja modern."
            },
            {
                "file_name": "05_revelation_machine_mindset.jpg",
                "timestamp": "[00:40 - 00:62] THE REVELATION (THE WHY)",
                "script_line": "Jadi masalah sebenarnya bukan AI yang mengambil alih hidup kita. Masalahnya adalah kita yang tanpa sadar memperlakukan diri kita sendiri seperti mesin: mengukur harga diri kita hanya dari seberapa cepat kita bisa berproduksi.",
                "visual_concept": "Sosok pekerja sendirian di tengah koridor gedung kaca modern yang dingin seperti roda gigi mesin",
                "search_query": "lone figure standing inside vast glass corporate skyscraper cold industrial architecture feeling small",
                "b_roll_cue": "Slow pull-back shot (zoom out). Suasana dingin gedung kaca memperkuat narasi manusia yang mengobjektifikasi dirinya jadi mesin."
            },
            {
                "file_name": "06_ending_pause_and_breathe.jpg",
                "timestamp": "[00:62 - 00:75] OPEN QUESTION (PENUTUP REFLEKTIF)",
                "script_line": "Kalau mesin memang diciptakan untuk bekerja tanpa henti, bukankah yang membedakan kita sebagai manusia adalah keberanian untuk tahu kapan harus berhenti? Menurut Anda gimana?",
                "visual_concept": "Seseorang menutup laptop dan menatap keluar jendela dengan tenang menikmati udara dan hening",
                "search_query": "person closing laptop looking thoughtfully out window taking deep calm breath quiet sunset",
                "b_roll_cue": "Visual hening menatap cakrawala luar ruangan. Beri jeda subtitle 0.8 detik sebelum video berakhir."
            }
        ]
    },
    {
        "id": "narasi-02",
        "title": "Di Balik Alasan Gen Z Lebih Memilih Ngontrak",
        "pillar": "PROPERTY × HUMAN × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-02",
        "scenes": [
            {
                "file_name": "01_hook_young_renter_lifestyle.jpg",
                "timestamp": "[00:00 - 00:05] HOOK",
                "script_line": "Banyak orang tua sering heran dan nanya: 'Kenapa sih anak muda sekarang kok kayaknya santai banget dan lebih milih ngontrak dibanding beli rumah?'",
                "visual_concept": "Anak muda santai di kamar studio kontrakan/apartemen minimalis",
                "search_query": "young person sitting casually in small modest rented studio apartment living room thoughtfully",
                "b_roll_cue": "B-roll pembuka suasana santai kamar kos/kontrakan minimalis dengan estetika hangat anak muda."
            },
            {
                "file_name": "02_tension_coffee_vs_finances.jpg",
                "timestamp": "[00:05 - 00:18] TENSION & PARADOX",
                "script_line": "Banyak pengamat buru-buru menyimpulkan kalau Gen Z itu manja, boros kopi, atau terlalu cinta kebebasan nomaden. Tapi kalau kita buka data kenaikan harga tanah dibanding pertumbuhan gaji riil lima tahun terakhir...",
                "visual_concept": "Segelas es kopi kekinian di atas meja dengan kalkulator atau catatan tagihan keuangan",
                "search_query": "young adult drinking artisanal iced coffee while looking worried at financial bills calculator",
                "b_roll_cue": "Transisi kontras dari gelas kopi mahal ke layar handphone yang menampilkan grafik harga properti."
            },
            {
                "file_name": "03_data_suburban_cluster_roofs.jpg",
                "timestamp": "[00:18 - 00:29] CONTEXT & THE REAL DATA (Part 1)",
                "script_line": "Kenyataannya, survei membuktikan mayoritas anak muda sebenarnya tetap mendambakan punya rumah sendiri. Tapi ketika harga rumah sederhana di pinggiran kota menuntut cicilan separuh gaji selama 25 tahun...",
                "visual_concept": "Deretan rumah kluster perumahan pinggiran kota yang seragam dan rapat",
                "search_query": "rows of identical modern suburban residential houses roofs residential real estate cluster",
                "b_roll_cue": "Overhead/street perspective deretan atap rumah perumahan kluster pinggiran yang berjarak jauh."
            },
            {
                "file_name": "04_data_commuter_train_fatigue.jpg",
                "timestamp": "[00:29 - 00:40] CONTEXT & THE REAL DATA (Part 2)",
                "script_line": "...otak manusia secara alami menyalakan mekanisme pertahanan diri: merasionalisasi keadaan.",
                "visual_concept": "Pekerja muda kelelahan bersandar di kaca jendela kereta komuter padat sepulang kerja",
                "search_query": "exhausted young commuter standing on crowded public train looking out window tired after long day",
                "b_roll_cue": "Refleksi wajah lelah di jendela gerbong KRL/kereta komuter, memperkuat realitas hidup suburban."
            },
            {
                "file_name": "05_revelation_warm_sanctuary.jpg",
                "timestamp": "[00:40 - 00:62] THE REVELATION (THE WHY)",
                "script_line": "Dalam psikologi, ketika sebuah kebutuhan dasar terasa mustahil dijangkau oleh perhitungan matematika, orang akan menutupi rasa putus asanya dengan narasi gaya hidup: 'Ah, ngontrak lebih fleksibel kok.' Padahal di lubuk hati terdalam, manusia purba di dalam diri kita tetap butuh sepetak ruang aman yang nggak bisa digusur siapa pun.",
                "visual_concept": "Kamar tidur bernuansa hangat dengan pencahayaan lampu temaram, simbol sanctuary rasa aman",
                "search_query": "cozy warm peaceful bedroom safe sanctuary warm lighting home comfort safe haven",
                "b_roll_cue": "Slow dissolve ke pencahayaan lembut kamar yang hangat. Memunculkan kerinduan psikologis akan 'rumah yang sesungguhnya'."
            },
            {
                "file_name": "06_ending_house_keys_table.jpg",
                "timestamp": "[00:62 - 00:75] OPEN QUESTION (PENUTUP REFLEKTIF)",
                "script_line": "Menurut Anda, apakah generasi muda sekarang beneran menikmati hidup nomaden, atau kita cuma sedang belajar menertawakan sesuatu yang nggak sanggup kita beli?",
                "visual_concept": "Tangan memegang gantungan kunci rumah di atas meja kayu dengan pencahayaan sinematik",
                "search_query": "person hand holding single metal house key on simple wooden table moody cinematic lighting",
                "b_roll_cue": "Close up kunci rumah di atas meja kayu. Tahan visual hingga detik terakhir untuk efek perenungan mendalam."
            }
        ]
    },
    {
        "id": "narasi-03",
        "title": "Ilusi Ruko Kosong di Tengah Kota yang Bising",
        "pillar": "AI × PROPERTY × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-03",
        "scenes": [
            {
                "file_name": "01_hook_empty_shophouses_street.jpg",
                "timestamp": "[00:00 - 00:05] HOOK",
                "script_line": "Coba perhatikan pas lagi jalan di tengah kota: jalanan macet parah, orang lalu-lalang, tapi kenapa deretan ruko tiga lantai di pinggir jalan justru makin banyak yang kosong dan berdebu?",
                "visual_concept": "Ruko toko tutup dengan rolling door besi berdebu di pinggir jalan raya protokol kota",
                "search_query": "abandoned empty street shop closed metal rolling shutter gate dusty sidewalk urban storefront",
                "b_roll_cue": "Shot kontras antara jalan aspal ramai di depan dan deretan rolling door besi ruko yang kusam terkunci rapat."
            },
            {
                "file_name": "02_tension_for_rent_commercial.jpg",
                "timestamp": "[00:05 - 00:18] TENSION & PARADOX",
                "script_line": "Dulu, rumus emas bisnis itu cuma tiga: lokasi, lokasi, dan lokasi di jalan protokol. Tapi hari ini, punya toko di pinggir jalan raya utama bukan lagi jaminan ramai pembeli. Justru sebaliknya: banyak pemilik ruko yang mulai kebingungan bayar bunga bank.",
                "visual_concept": "Plang 'Disewa / Dijual' menempel pada kaca ruko kosong berdebu",
                "search_query": "for rent lease sign on dusty glass window of empty commercial retail building vacant store",
                "b_roll_cue": "Macro focus pada plang 'For Rent' / 'Disewa' yang mulai pudar di balik kaca toko kusam."
            },
            {
                "file_name": "03_data_delivery_courier_traffic.jpg",
                "timestamp": "[00:18 - 00:29] CONTEXT & THE REAL DATA (Part 1)",
                "script_line": "Apa yang sebenarnya terjadi? Sederhana: internet, logistik kurir, dan sistem automasi AI diam-diam telah memindahkan aliran darah ekonomi kita. Dulu, jalan aspal adalah tempat bertemunya penjual dan pembeli. Sekarang, jalan raya cuma jadi jalur motor kurir...",
                "visual_concept": "Kurir motor ekspedisi membawa tumpukan kardus paket di tengah kemacetan jalan kota",
                "search_query": "delivery courier driver riding motorcycle on busy city road carrying parcel boxes bags",
                "b_roll_cue": "Cut cepat ke motor kurir pengantar paket melintas di aspal jalanan, visualisasi 'aliran darah ekonomi baru'."
            },
            {
                "file_name": "04_data_automated_warehouse.jpg",
                "timestamp": "[00:29 - 00:40] CONTEXT & THE REAL DATA (Part 2)",
                "script_line": "...mengantarkan barang yang dibeli lewat layar ponsel dari gudang murah di pinggiran kota.",
                "visual_concept": "Gudang logistik e-commerce otomatis rak-rak tinggi penuh kardus paket",
                "search_query": "modern automated logistics warehouse high shelves stacked cardboard boxes e-commerce distribution",
                "b_roll_cue": "Visual megah lorong gudang distribusi pinggiran kota dengan rak palet bertingkat."
            },
            {
                "file_name": "05_revelation_sensory_cafe_meeting.jpg",
                "timestamp": "[00:40 - 00:62] THE REVELATION (THE WHY)",
                "script_line": "Artinya, fungsi ruang fisik kota sedang dipaksa berubah total. Ruang beton yang cuma nawarin fungsi transaksi jual-beli biasa pelan-pelan akan mati. Yang bertahan cuma ruang fisik yang menawarkan apa yang nggak bisa dikirim kurir: pengalaman indra manusia, keheningan, dan perjumpaan tatap muka nyata.",
                "visual_concept": "Kafe estetik dengan interaksi hangat tatap muka, secangkir kopi, dan tawa manusia nyata",
                "search_query": "warm aesthetic artisan coffee shop people engaged in genuine face to face conversation laughter",
                "b_roll_cue": "Warm grading filter. Visual orang menikmati obrolan langsung dan aroma kopi. Kontras dengan beton ruko yang mati."
            },
            {
                "file_name": "06_ending_city_skyline_dusk.jpg",
                "timestamp": "[00:62 - 00:75] OPEN QUESTION (PENUTUP REFLEKTIF)",
                "script_line": "Kalau semua transaksi belanja pindah ke algoritma cloud, kira-kira sepuluh tahun lagi gedung-gedung ruko di tengah kota kita bakal berubah jadi apa ya?",
                "visual_concept": "Pemandangan cakrawala kota saat senja dengan lampu jalanan mulai menyala",
                "search_query": "moody dusk view of city commercial buildings and illuminated street reflections urban future",
                "b_roll_cue": "Cinematic wide angle senja kota metropolis. Menutup dengan kesan megah dan futuristik."
            }
        ]
    },
    {
        "id": "narasi-04",
        "title": "Harga Nyata yang Kita Bayar untuk Otomasi 5 Detik",
        "pillar": "TECHNOLOGY × WORK × HUMAN × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-04",
        "scenes": [
            {
                "file_name": "01_hook_fast_scrolling_screen.jpg",
                "timestamp": "[00:00 - 00:05] HOOK",
                "script_line": "Cuma butuh lima detik buat AI bikin ringkasan dokumen 50 halaman. Tapi pernah nggak Anda hitung, apa harga mahal yang diam-diam sedang kita bayar untuk kemudahan itu?",
                "visual_concept": "Jari jempol scrolling sangat cepat di layar HP menyala dalam kegelapan",
                "search_query": "close up fingers rapidly scrolling on glowing smartphone screen blue light darkness",
                "b_roll_cue": "Close up ekstrem ibu jari scrolling tiada henti dengan pendaran cahaya biru di wajah."
            },
            {
                "file_name": "02_tension_book_vs_phone_buzz.jpg",
                "timestamp": "[00:05 - 00:18] TENSION & PARADOX",
                "script_line": "Kita merasa semakin cerdas karena bisa tahu intisari segala hal dalam hitungan detik. Tapi anehnya, di saat yang sama, kemampuan kita untuk duduk tenang membaca satu bab buku tanpa gelisah meraih HP justru hampir lenyap sama sekali.",
                "visual_concept": "Buku cetak terbuka di atas meja di samping smartphone menyala notifikasi",
                "search_query": "open paper book on wooden desk next to a glowing smartphone screen showing notifications",
                "b_roll_cue": "Fokus berganti (rack focus) dari halaman buku kertas yang tenang ke layar HP yang bergetar."
            },
            {
                "file_name": "03_data_deep_thought_journaling.jpg",
                "timestamp": "[00:18 - 00:40] CONTEXT & THE REAL DATA",
                "script_line": "Riset neurosains berulang kali membuktikan: otak manusia tidak membentuk wawasan mendalam dari kesimpulan instan. Pemikiran kritis dan intuisi kreatif justru lahir saat otak kita berjuang mencerna detail yang rumit, merasakan kebosanan, dan menemukan polanya sendiri secara perlahan.",
                "visual_concept": "Seseorang menulis tangan perlahan di buku jurnal dengan pensil, fokus dan tenang",
                "search_query": "person writing slowly with pencil in paper journal notebook thoughtful slow reflection",
                "b_roll_cue": "Gerakan lambat goresan pensil di atas kertas. Visualisasi 'deep work' dan pergulatan nalar manusia."
            },
            {
                "file_name": "04_revelation_blue_light_anxiety.jpg",
                "timestamp": "[00:40 - 00:51] THE REVELATION (THE WHY - Part 1)",
                "script_line": "Saat kita menyerahkan seluruh proses pergulatan berpikir itu ke algoritma, kita memang menghemat waktu di jam kerja. Tapi kita membayar kompensasinya dengan menukar ketajaman nalar biologis kita...",
                "visual_concept": "Wajah cemas seseorang yang hanya disinari oleh cahaya dingin layar ponsel di ruangan gelap",
                "search_query": "anxious young person face illuminated solely by smartphone screen in pitch black dark room",
                "b_roll_cue": "Visual dramatis pendaran cahaya layar pada mata yang gelisah di dalam kegelapan total."
            },
            {
                "file_name": "05_revelation_phone_absorbed_crowd.jpg",
                "timestamp": "[00:51 - 00:62] THE REVELATION (THE WHY - Part 2)",
                "script_line": "...menjadi konsumen konten yang gampang cemas dan gampang disetir opini luar.",
                "visual_concept": "Kerumunan orang di kereta atau ruang publik semuanya menunduk menatap layar masing-masing",
                "search_query": "crowd of people in subway metro train all heads down staring at mobile phone screens",
                "b_roll_cue": "Sudut pandang luas kerumunan komuter tanpa saling tegur, semuanya terhipnotis layar masing-masing."
            },
            {
                "file_name": "06_ending_peaceful_mind_nature.jpg",
                "timestamp": "[00:62 - 00:75] OPEN QUESTION (PENUTUP REFLEKTIF)",
                "script_line": "Kapan terakhir kali Anda duduk melamun sepuluh menit penuh tanpa ada layar menyala di depan mata, dan membiarkan pikiran Anda bernapas sendiri?",
                "visual_concept": "Seseorang duduk tenang di alam terbuka tanpa gadget, mata terpejam menghirup udara segar",
                "search_query": "peaceful person sitting alone outdoors on park bench breathing calmly eyes closed relaxed",
                "b_roll_cue": "Visual santai di taman terbuka hijau. Tahan frame 1 detik tanpa teks setelah pertanyaan selesai."
            }
        ]
    },
    {
        "id": "narasi-05",
        "title": "Kenapa Tanah Makin Mahal Justru Saat Dunia Makin Virtual?",
        "pillar": "FUTURE × PROPERTY × HUMAN × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-05",
        "scenes": [
            {
                "file_name": "01_hook_virtual_reality_tech.jpg",
                "timestamp": "[00:00 - 00:05] HOOK",
                "script_line": "Pernah kepikiran nggak: kalau masa depan katanya ada di dunia digital, AI, dan metaverse, kenapa orang-orang paling kaya di industri teknologi justru berlomba-lomba beli ribuan hektar tanah fisik di dunia nyata?",
                "visual_concept": "Seseorang memakai kacamata VR headset dengan pendaran neon digital futuristik",
                "search_query": "person wearing futuristic virtual reality vr headset in neon cyber digital lighting",
                "b_roll_cue": "Visual berkecepatan tinggi pendaran neon digital dan kacamata VR, simbol 'dunia virtual buatan'."
            },
            {
                "file_name": "02_tension_vast_green_valley.jpg",
                "timestamp": "[00:05 - 00:18] TENSION & PARADOX",
                "script_line": "Di internet, mereka menyuruh kita hidup di layar, kerja lewat cloud, dan bersenang-senang di ruang virtual. Tapi diam-diam, portofolio kekayaan mereka justru dilarikan ke aset paling kuno di muka bumi: tanah, air bersih, dan ruang terbuka hijau.",
                "visual_concept": "Lembah hijau membentang luas tak terjamah dengan langit biru jernih dan aliran air",
                "search_query": "vast breathtaking lush green valley hills rolling meadow untouched landscape under clear sky",
                "b_roll_cue": "Kontras drastis: potong dari neon VR ke lanskap alam hijau luas yang memukau mata."
            },
            {
                "file_name": "03_data_fertile_soil_seedling.jpg",
                "timestamp": "[00:18 - 00:40] CONTEXT & THE REAL DATA",
                "script_line": "Kenapa begitu kontradiktif? Jawabannya ada pada hukum dasar ekonomi: kelangkaan. Di era AI, apa pun yang bersifat digital—mulai dari baris kode, artikel pintar, foto, sampai video realistis—bisa digandakan sampai miliaran kali dengan biaya hampir nol rupiah. Semakin berlimpah sesuatu di dunia digital, nilainya akan semakin anjlok.",
                "visual_concept": "Sepasang tangan menangkup tanah subur hitam dengan tunas tanaman hijau kecil yang tumbuh",
                "search_query": "pair of hands cupping rich dark fertile garden soil with a tiny green seedling sprouting",
                "b_roll_cue": "Close up tangan menggenggam tanah basah subur. Menegaskan kontras antara 'kode digital tak terbatas' vs 'tanah fisik yang langka'."
            },
            {
                "file_name": "04_revelation_golden_sunlight_meadow.jpg",
                "timestamp": "[00:40 - 00:51] THE REVELATION (THE WHY - Part 1)",
                "script_line": "Kebalikannya, ada satu hal di alam semesta ini yang nggak akan pernah bisa digandakan oleh server tercanggih mana pun: sepetak tanah fisik di bawah sinar matahari.",
                "visual_concept": "Pancaran sinar matahari pagi menembus kanopi pepohonan hutan ke padang rumput",
                "search_query": "golden sun rays shining down through forest canopy onto fresh green grass morning light",
                "b_roll_cue": "Slow cinematic light ray (sunburst). Visual matahari nyata yang tidak bisa dibuat oleh GPU/server mana pun."
            },
            {
                "file_name": "05_revelation_cabin_nature_sanctuary.jpg",
                "timestamp": "[00:51 - 00:62] THE REVELATION (THE WHY - Part 2)",
                "script_line": "Ketika seluruh dunia dibanjiri kepalsuan buatan mesin, keaslian alam nyata dan ketenangan ruang fisik mendadak berubah jadi barang paling mewah di bumi.",
                "visual_concept": "Rumah kayu minimalis modern di tengah keasrian hutan hijau yang tenang",
                "search_query": "peaceful modern minimalist wooden architectural home nestled in lush forest mountain nature",
                "b_roll_cue": "Visual arsitektur hunian menyatu dengan alam. Menegaskan pesan bahwa ketenangan ruang fisik adalah kemewahan tertinggi."
            },
            {
                "file_name": "06_ending_legacy_parent_child.jpg",
                "timestamp": "[00:62 - 00:75] OPEN QUESTION (PENUTUP REFLEKTIF)",
                "script_line": "Di masa depan nanti saat kecerdasan bisa didownload gratis oleh siapa saja, menurut Anda apa satu hal nyata yang bakal jadi warisan paling berharga untuk anak cucu kita?",
                "visual_concept": "Orang tua dan anak kecil berjalan bergandengan tangan di padang rumput senja keemasan",
                "search_query": "father mother walking with small child across wide grassy meadow sunset golden hour warmth",
                "b_roll_cue": "Siluet hangat orang tua dan anak melangkah di tanah terbuka saat senja. Fade to black perlahan."
            }
        ]
    }
]

def main():
    session_id = init_mcp_session()
    
    overall_manifest = {}

    for plan in NARASI_PLANS:
        narasi_id = plan["id"]
        narasi_title = plan["title"]
        assets_dir = os.path.join(plan["folder"], "assets")
        os.makedirs(assets_dir, exist_ok=True)
        
        print(f"\n=======================================================")
        print(f"Processing {narasi_id}: {narasi_title}")
        print(f"Target folder: {assets_dir}")
        print(f"=======================================================")
        
        downloaded_assets = []
        
        for idx, scene in enumerate(plan["scenes"]):
            file_name = scene["file_name"]
            target_path = os.path.join(assets_dir, file_name)
            query = scene["search_query"]
            print(f"\n[{idx+1}/{len(plan['scenes'])}] Searching for: '{query}'...")
            
            try:
                results = search_photos(session_id, query, orientation="portrait")
                if not results:
                    print(f"  Warning: No portrait results for query, trying fallback broader search...")
                    results = search_photos(session_id, query[:60], orientation="portrait")
                
                if results:
                    chosen = results[0]
                    # Select the best high-res image url
                    urls = chosen.get("urls", {})
                    img_url = urls.get("large") or urls.get("regular") or urls.get("full") or chosen.get("image_url")
                    
                    print(f"  Downloading from: {img_url}")
                    size_bytes = download_image(img_url, target_path)
                    print(f"  Saved {file_name} ({size_bytes:,} bytes)")
                    
                    asset_info = {
                        "file_name": file_name,
                        "timestamp": scene["timestamp"],
                        "script_line": scene["script_line"],
                        "visual_concept": scene["visual_concept"],
                        "b_roll_cue": scene["b_roll_cue"],
                        "photo_id": chosen.get("photo_id"),
                        "photographer": chosen.get("photographer_username") or chosen.get("photographer") or "Pexels Creator",
                        "source": chosen.get("source", "Pexels"),
                        "license": chosen.get("license_type", "Free to use"),
                        "source_url": chosen.get("source_image_url") or chosen.get("image_url"),
                        "description": chosen.get("description") or chosen.get("source_description", ""),
                        "dimensions": f"{chosen.get('width', '-')} x {chosen.get('height', '-')}",
                        "orientation": chosen.get("orientation", "portrait")
                    }
                    downloaded_assets.append(asset_info)
                else:
                    print(f"  ERROR: No image found for scene {file_name}")
            except Exception as e:
                print(f"  Error processing scene {file_name}: {e}")
            
            time.sleep(0.5)
            
        # Write ASSETS_INDEX.md in assets/ folder
        index_md_path = os.path.join(assets_dir, "ASSETS_INDEX.md")
        with open(index_md_path, "w", encoding="utf-8") as f:
            f.write(f"# 📸 Index Aset Visual: {narasi_title}\n\n")
            f.write(f"- **Pilar DNA:** `{plan['pillar']}`\n")
            f.write(f"- **Format:** Vertical 9:16 (TikTok / Instagram Reels / YouTube Shorts)\n")
            f.write(f"- **Penyedia Aset:** Pexafy MCP (Pexels / Pixabay License Free)\n\n")
            f.write(f"---\n\n")
            f.write(f"## 📋 Daftar Aset & Petunjuk Editing (B-Roll Cue Sheet)\n\n")
            
            for item in downloaded_assets:
                f.write(f"### 🖼️ `{item['file_name']}`\n")
                f.write(f"- **Timeline Naskah:** `{item['timestamp']}`\n")
                f.write(f"- **Kutipan Naskah:** *\"{item['script_line']}\"*\n")
                f.write(f"- **Konsep Visual:** {item['visual_concept']}\n")
                f.write(f"- **🎬 Instruksi Editor (B-Roll):** {item['b_roll_cue']}\n")
                f.write(f"- **Fotografer / Author:** {item['photographer']} ({item['source']})\n")
                f.write(f"- **Resolusi Asli:** {item['dimensions']} | Orientasi: {item['orientation']}\n")
                f.write(f"- **Deskripsi Gambar:** {item['description']}\n")
                f.write(f"- **Sumber URL:** [{item['source']}]({item['source_url']})\n\n")
                f.write(f"---\n\n")
                
        print(f"Generated index: {index_md_path}")
        
        # Write SCRIPT_AND_STORYBOARD.md in root of narasi folder
        storyboard_path = os.path.join(plan["folder"], "SCRIPT_AND_STORYBOARD.md")
        with open(storyboard_path, "w", encoding="utf-8") as f:
            f.write(f"# 🎬 Storyboard & Naskah Produksi: {narasi_title}\n\n")
            f.write(f"**Pilar Konten:** `{plan['pillar']}`  \n")
            f.write(f"**Karakter Suara:** Conversational, jujur, tenang, reflektif, tanpa jargon klise AI.  \n")
            f.write(f"**Rasio Video:** 9:16 Vertical Video (TikTok / Shorts / Reels)  \n\n")
            f.write(f"---\n\n")
            f.write(f"## 🎞️ Storyboard Sekuensial (Talking Head + B-Roll Overlay)\n\n")
            f.write(f"| Timestamp | Tipe Visual | Aset B-Roll | Panduan Kamera / Editor |\n")
            f.write(f"| :--- | :--- | :--- | :--- |\n")
            for item in downloaded_assets:
                f.write(f"| `{item['timestamp']}` | Talking Head + B-Roll Cut | `assets/{item['file_name']}` | {item['b_roll_cue']} |\n")
            f.write(f"\n---\n\n")
            f.write(f"## 📜 Naskah Lengkap & Cue Aset\n\n")
            for item in downloaded_assets:
                f.write(f"#### {item['timestamp']}\n")
                f.write(f"> **NUGI (Talking Head):**\n")
                f.write(f"> \"{item['script_line']}\"\n\n")
                f.write(f"*(🎬 **B-ROLL CUE:** Tampilkan `assets/{item['file_name']}` - {item['visual_concept']} - {item['b_roll_cue']})*\n\n")
                
        print(f"Generated storyboard: {storyboard_path}")
        overall_manifest[narasi_id] = downloaded_assets

    # Save overall manifest
    manifest_path = r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\OVERALL_ASSETS_MANIFEST.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(overall_manifest, f, indent=2)
    print(f"\nCompleted! All 5 narasi processed and saved to {manifest_path}")

if __name__ == "__main__":
    main()
