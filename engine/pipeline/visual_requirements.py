"""
engine/pipeline/visual_requirements.py
======================================
Transforms parsed script sections into a sequence of dynamic visual shot requirements.

Editing Principles:
  - Faceless visual essay / mini-documentary aesthetic
  - No static slideshows: longer sections are cut into dynamic sub-shots (3–7s pacing)
  - Progression follows narrative meaning:
      working human → AI/tech → pressure/exhaustion → data/proof → metaphor → resolution
  - Short, punchy text overlays for core phrases
  - Prioritizes real archival footage, documentary photos, and visual metaphors
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from engine.pipeline.script_parser import NarasiScript, ScriptSection


@dataclass
class VisualShotRequirement:
    """Requirement for a single visual shot on the timeline."""
    shot_id: str
    section_index: int
    section_name: str
    section_type: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    visual_description: str
    search_query: str
    fallback_queries: List[str] = field(default_factory=list)
    text_overlay: str = ""
    preferred_media_type: str = "any"  # "video", "image", or "any"
    visual_metaphor: str = ""

    @property
    def start_frame(self) -> int:
        return int(round(self.start_seconds * 30))

    @property
    def end_frame(self) -> int:
        return int(round(self.end_seconds * 30)) - 1

    @property
    def duration_frames(self) -> int:
        return max(1, self.end_frame - self.start_frame + 1)


# Hand-crafted documentary shot design for Nugi's 5 core scripts
_CURATED_NARRATIVE_SHOTS: Dict[int, List[Dict]] = {
    1: [  # AI × HUMAN: Mengapa AI Bikin Cepat, tapi Kita Justru Makin Capek?
        {
            "sec_idx": 1, "dur_ratio": 1.0,
            "desc": "Pekerja kantor tampak kelelahan menatap layar monitor di kantor larut malam",
            "query": "exhausted office worker computer night desk",
            "fallbacks": ["overworked employee tired laptop", "office night worker fatigue"],
            "overlay": "Jam Kerja Berantakan?", "metaphor": "Kelelahan modern",
        },
        {
            "sec_idx": 2, "dur_ratio": 0.5,
            "desc": "Animasi kode komputer dan automasi data bergerak sangat cepat",
            "query": "fast computer code automation data processing screen",
            "fallbacks": ["digital automation artificial intelligence software", "high speed data stream"],
            "overlay": "2 Jam Jadi 2 Menit", "metaphor": "Kecepatan mesin",
        },
        {
            "sec_idx": 2, "dur_ratio": 0.5,
            "desc": "Karyawan korporat memijat dahi menahan kantuk dan pusing di depan meja",
            "query": "stressed tired worker rubbing eyes headache desk",
            "fallbacks": ["exhausted business professional office fatigue", "tired worker desk"],
            "overlay": "Makin Capek?", "metaphor": "Beban kognitif",
        },
        {
            "sec_idx": 3, "dur_ratio": 0.33,
            "desc": "Tumpukan dokumen laporan keuangan dan grafik spreadsheet korporat",
            "query": "business reports financial charts documents paperwork desk",
            "fallbacks": ["corporate audit paper documents stack", "spreadsheet financial data"],
            "overlay": "Tuntutan Kuota Berlipat", "metaphor": "Beban kuota",
        },
        {
            "sec_idx": 3, "dur_ratio": 0.33,
            "desc": "Suasana lantai kantor yang sibuk dan penuh tekanan kerja tinggi",
            "query": "busy corporate office floor pressure workers deadline",
            "fallbacks": ["hectic modern corporate workspace employees", "open office busy work"],
            "overlay": "5 Laporan Sehari", "metaphor": "Tekanan waktu",
        },
        {
            "sec_idx": 3, "dur_ratio": 0.34,
            "desc": "Server data center dengan lampu berkedip melambangkan infrastruktur AI",
            "query": "data center server racks blinking lights networking",
            "fallbacks": ["supercomputer mainframe computing facility", "cloud servers data"],
            "overlay": "Kan Ada AI?", "metaphor": "Ilusi otomatisasi",
        },
        {
            "sec_idx": 4, "dur_ratio": 0.33,
            "desc": "Pabrik industri lama dengan pekerja seperti roda penggerak mesin",
            "query": "industrial assembly line factory machinery vintage",
            "fallbacks": ["factory production line workers machinery", "industrial gears working"],
            "overlay": "Memperlakukan Diri Seperti Mesin", "metaphor": "Manusia mesin",
        },
        {
            "sec_idx": 4, "dur_ratio": 0.33,
            "desc": "Timelapse jam dinding berputar cepat melambangkan tekanan produktivitas",
            "query": "clock ticking timelapse speed pressure time passing",
            "fallbacks": ["analog clock dial spinning fast", "stopwatch timing pressure"],
            "overlay": "Seberapa Cepat Berproduksi?", "metaphor": "Harga diri produksi",
        },
        {
            "sec_idx": 4, "dur_ratio": 0.34,
            "desc": "Siluet manusia sendirian memandang ke luar jendela gedung kota",
            "query": "silhouette person looking out window city evening reflective",
            "fallbacks": ["thoughtful human silhouette glass window high building", "lone person city sunset"],
            "overlay": "Manusia Bukan Mesin", "metaphor": "Kesadaran diri",
        },
        {
            "sec_idx": 5, "dur_ratio": 0.5,
            "desc": "Seseorang berjalan perlahan di jalan setapak taman rindang dan tenang",
            "query": "person walking in peaceful green park path nature",
            "fallbacks": ["solitary walk nature forest peaceful", "quiet park trees sunlight"],
            "overlay": "Kapan Harus Berhenti?", "metaphor": "Ketenangan",
        },
        {
            "sec_idx": 5, "dur_ratio": 0.5,
            "desc": "Tangan menutup laptop perlahan di meja kafe yang tenang saat sore",
            "query": "closing laptop end of work day evening desk",
            "fallbacks": ["shutting laptop relaxed finish work", "hands closing laptop quiet room"],
            "overlay": "Keberanian Berhenti", "metaphor": "Batasan manusia",
        },
    ],
    2: [  # PROPERTY × HUMAN: Di Balik Alasan Gen Z Lebih Memilih Ngontrak
        {
            "sec_idx": 1, "dur_ratio": 1.0,
            "desc": "Anak muda berjalan di kawasan apartemen perkotaan modern",
            "query": "young people urban city street apartment building",
            "fallbacks": ["young adults walking city residential street", "urban lifestyle youth"],
            "overlay": "Milih Ngontrak?", "metaphor": "Pilihan generasi",
        },
        {
            "sec_idx": 2, "dur_ratio": 0.5,
            "desc": "Grafik kenaikan harga properti dan tanah melonjak tajam",
            "query": "housing price inflation chart real estate market graph",
            "fallbacks": ["rising cost of living financial chart", "real estate price trend"],
            "overlay": "Harga Tanah Melejit", "metaphor": "Jurang realitas",
        },
        {
            "sec_idx": 2, "dur_ratio": 0.5,
            "desc": "Anak muda memeriksa dompet dan rekening dengan ekspresi cemas",
            "query": "young professional calculating budget bills worried desk",
            "fallbacks": ["person counting money worried financial budget", "student checking bills"],
            "overlay": "Gaji Tak Terkejar", "metaphor": "Tekanan ekonomi",
        },
        {
            "sec_idx": 3, "dur_ratio": 0.33,
            "desc": "Pemandangan udara kompleks perumahan pinggiran kota yang padat",
            "query": "aerial suburban housing tract development residential",
            "fallbacks": ["dense suburban neighborhood rows of houses", "suburban houses aerial"],
            "overlay": "Rumah Pinggiran Kota", "metaphor": "Jarak fisik",
        },
        {
            "sec_idx": 3, "dur_ratio": 0.33,
            "desc": "Penandatanganan berkas KPR dan cicilan bank jangka panjang 25 tahun",
            "query": "mortgage bank loan contract signing paperwork documents",
            "fallbacks": ["home buying contract real estate agreement", "signing bank debt papers"],
            "overlay": "Cicilan 25 Tahun", "metaphor": "Beban seumur hidup",
        },
        {
            "sec_idx": 3, "dur_ratio": 0.34,
            "desc": "Konsep psikologi kognitif dan mekanisme pertahanan pikiran manusia",
            "query": "abstract human brain thoughts psychology cognitive concept",
            "fallbacks": ["human mind neural thinking artistic", "psychological reflection silhouette"],
            "overlay": "Mekanisme Pertahanan", "metaphor": "Rasionalisasi",
        },
        {
            "sec_idx": 4, "dur_ratio": 0.33,
            "desc": "Kamar kos atau apartemen sewa sederhana dengan koper anak muda",
            "query": "young person moving boxes rented apartment living room",
            "fallbacks": ["studio apartment rental youth luggage", "cozy rented bedroom minimal"],
            "overlay": "Ngontrak Lebih Fleksibel?", "metaphor": "Kover gaya hidup",
        },
        {
            "sec_idx": 4, "dur_ratio": 0.33,
            "desc": "Rumah bernuansa hangat dengan lampu menyala di senja hari",
            "query": "warm cozy home interior safe shelter evening light",
            "fallbacks": ["peaceful living room warm lights home", "safe comfortable home hearth"],
            "overlay": "Sepetak Ruang Aman", "metaphor": "Kebutuhan dasar",
        },
        {
            "sec_idx": 4, "dur_ratio": 0.34,
            "desc": "Ilustrasi arkeologi tempat perlindungan manusia purba",
            "query": "ancient cave shelter primitive stone hearth archaeology",
            "fallbacks": ["prehistoric human shelter cave painting", "primitive wooden hut hearth"],
            "overlay": "Insting Purba Manusia", "metaphor": "Akar biologis",
        },
        {
            "sec_idx": 5, "dur_ratio": 0.5,
            "desc": "Pemuda dengan ransel berdiri di peron stasiun kereta urban sendirian",
            "query": "solitary commuter backpack train station platform transit",
            "fallbacks": ["nomad traveler urban city station alone", "young commuter transit"],
            "overlay": "Beneran Nikmat Nomaden?", "metaphor": "Pertanyaan reflektif",
        },
        {
            "sec_idx": 5, "dur_ratio": 0.5,
            "desc": "Gedung-gedung rumah kota di kejauhan dengan langit senja temaram",
            "query": "city sunset skyline residential buildings distant horizon",
            "fallbacks": ["evening city housing rooftops sunset sky", "urban houses sunset dusk"],
            "overlay": "Atau Tak Sanggup Beli?", "metaphor": "Realitas akhir",
        },
    ],
    3: [  # AI × PROPERTY: Ilusi Ruko Kosong di Tengah Kota yang Bising
        {
            "sec_idx": 1, "dur_ratio": 1.0,
            "desc": "Deretan ruko 3 lantai tutup dengan pintu rolling door berdebu di pinggir jalan",
            "query": "empty commercial shophouses closed roller shutter street",
            "fallbacks": ["abandoned shopfront commercial real estate", "shuttered retail stores city"],
            "overlay": "Ruko Kosong Tengah Kota", "metaphor": "Paradoks fisik",
        },
        {
            "sec_idx": 2, "dur_ratio": 0.5,
            "desc": "Kemacetan lalu lintas mobil dan motor di jalan protokol kota besar",
            "query": "heavy city traffic jam main avenue busy downtown street",
            "fallbacks": ["crowded metropolitan avenue cars congestion", "city street rush hour traffic"],
            "overlay": "Jalanan Macet Parah", "metaphor": "Keramaian semu",
        },
        {
            "sec_idx": 2, "dur_ratio": 0.5,
            "desc": "Spanduk 'DISEWA / DIJUAL' tergantung pada ruko sepi berdebu",
            "query": "for lease for sale banner commercial property building",
            "fallbacks": ["vacant commercial retail space for rent sign", "closed store building"],
            "overlay": "Lokasi Bukan Jaminan", "metaphor": "Matinya rumus lama",
        },
        {
            "sec_idx": 3, "dur_ratio": 0.33,
            "desc": "Kurir motor ekspedisi mengantarkan paket kardus di tengah jalan",
            "query": "delivery courier motorcycle package parcel city transit",
            "fallbacks": ["motorcycle delivery courier parcel box road", "fast logistics courier street"],
            "overlay": "Aliran Darah Ekonomi Pindah", "metaphor": "Logistik modern",
        },
        {
            "sec_idx": 3, "dur_ratio": 0.33,
            "desc": "Gudang raksasa e-commerce modern dengan rak tinggi dan forklift otomatis",
            "query": "automated warehouse logistics fulfillment center boxes forklift",
            "fallbacks": ["giant logistics distribution center shipping", "ecommerce fulfillment warehouse"],
            "overlay": "Gudang Murah Pinggiran", "metaphor": "Perpindahan pusat",
        },
        {
            "sec_idx": 3, "dur_ratio": 0.34,
            "desc": "Jari menekan aplikasi belanja online di layar ponsel pintar",
            "query": "person ordering shopping smartphone app checkout screen",
            "fallbacks": ["mobile phone online shopping payment fingertip", "ecommerce buying phone screen"],
            "overlay": "Beli Lewat Layar", "metaphor": "Transaksi digital",
        },
        {
            "sec_idx": 4, "dur_ratio": 0.33,
            "desc": "Dinding beton ruko kosong dengan bayangan sinar matahari sore",
            "query": "empty concrete retail space vacant architectural interior",
            "fallbacks": ["abandoned modern retail room bare concrete", "empty shop interior sunlight"],
            "overlay": "Fungsi Ruang Berubah", "metaphor": "Ruang mati",
        },
        {
            "sec_idx": 4, "dur_ratio": 0.33,
            "desc": "Orang-orang berkumpul, bercengkrama hangat di kafe bernuansa estetis",
            "query": "people enjoying conversation cozy cafe social gathering",
            "fallbacks": ["friends talking laughing coffee shop warm lighting", "social gathering cafe table"],
            "overlay": "Pengalaman Indra Nyata", "metaphor": "Kebutuhan tatap muka",
        },
        {
            "sec_idx": 4, "dur_ratio": 0.34,
            "desc": "Halaman terbuka rindang dengan tanaman hijau di tengah kawasan kota",
            "query": "quiet urban courtyard garden trees sunlight sanctuary",
            "fallbacks": ["tranquil green space city atrium sunlight", "peaceful urban garden path"],
            "overlay": "Yang Tak Bisa Dikirim Kurir", "metaphor": "Keheningan",
        },
        {
            "sec_idx": 5, "dur_ratio": 0.5,
            "desc": "Visualisasi abstrak cloud computing dan aliran data belanja digital",
            "query": "abstract cloud computing network digital flow glowing nodes",
            "fallbacks": ["digital ecommerce cyberspace network abstract", "data connections cloud futuristic"],
            "overlay": "Algoritma Cloud", "metaphor": "Dunia tak kasat mata",
        },
        {
            "sec_idx": 5, "dur_ratio": 0.5,
            "desc": "Ruko-ruko tua di perkotaan dengan langit senja dramatis",
            "query": "urban shophouses architectural skyline evening dramatic sky",
            "fallbacks": ["traditional city shophouse street dusk", "urban buildings sunset horizon"],
            "overlay": "Bakal Jadi Apa?", "metaphor": "Masa depan ruang",
        },
    ],
    4: [  # TECHNOLOGY × WORK × HUMAN: Harga Nyata yang Kita Bayar untuk Otomasi 5 Detik
        {
            "sec_idx": 1, "dur_ratio": 1.0,
            "desc": "AI membuat ringkasan teks kilat otomatis di layar komputer",
            "query": "ai text prompt generator automatic document summary screen",
            "fallbacks": ["artificial intelligence typing text interface", "ai chatbot processing documents"],
            "overlay": "Ringkasan Dokumen 5 Detik", "metaphor": "Kecepatan instan",
        },
        {
            "sec_idx": 2, "dur_ratio": 0.5,
            "desc": "Seseorang menatap smartphone dengan notifikasi bertubi-tubi",
            "query": "person scrolling smartphone infinite notifications glowing face",
            "fallbacks": ["distracted person mobile phone screen glow", "social media notification feed user"],
            "overlay": "Merasa Tambah Cerdas?", "metaphor": "Fragmentasi fokus",
        },
        {
            "sec_idx": 2, "dur_ratio": 0.5,
            "desc": "Buku terbuka di meja tapi orangnya gelisah meraih ponsel",
            "query": "open book desk restless hand grabbing smartphone distraction",
            "fallbacks": ["person unable to read book reaching for phone", "distracted reader desk book phone"],
            "overlay": "Sulit Duduk Tenang", "metaphor": "Hilangnya kesabaran",
        },
        {
            "sec_idx": 3, "dur_ratio": 0.33,
            "desc": "Visualisasi anatomi otak manusia dan sinapsis saraf berpikir mendalam",
            "query": "human brain neural synapses neuroscience cognitive thoughts",
            "fallbacks": ["brain neural activity scan medical visualization", "deep thinking mind abstract"],
            "overlay": "Neurosains & Pemikiran Kritis", "metaphor": "Biologi pikiran",
        },
        {
            "sec_idx": 3, "dur_ratio": 0.33,
            "desc": "Seseorang membaca teks buku tebal dan mencatat dengan pensil secara saksama",
            "query": "student researcher studying deep complex book library pencil",
            "fallbacks": ["person deep reading taking notes paper notebook", "serious reader library books"],
            "overlay": "Mencerna Detail Rumit", "metaphor": "Pergulatan ide",
        },
        {
            "sec_idx": 3, "dur_ratio": 0.34,
            "desc": "Sketsa ide kreatif di buku catatan lahir perlahan dari lamunan",
            "query": "creative sketches handwritten diagram notebook ideas flow",
            "fallbacks": ["artist drafting concepts paper slow creative process", "hand drawing notebook creative"],
            "overlay": "Intuisi Kreatif", "metaphor": "Lahirnya wawasan",
        },
        {
            "sec_idx": 4, "dur_ratio": 0.33,
            "desc": "Arus data kode biner berulang-ulang tanpa emosi di monitor",
            "query": "endless binary code data stream algorithm processing",
            "fallbacks": ["cyber code data matrix digital stream", "algorithms code running screen"],
            "overlay": "Menyerahkan Proses Berpikir", "metaphor": "Otomasi nalar",
        },
        {
            "sec_idx": 4, "dur_ratio": 0.33,
            "desc": "Orang cemas menatap cahaya layar di ruangan gelap gulita",
            "query": "anxious person scrolling phone dark room face illuminated",
            "fallbacks": ["lonely person dark room screen light anxiety", "stressed individual phone glow dark"],
            "overlay": "Gampang Cemas & Disetir", "metaphor": "Ketergantungan opini",
        },
        {
            "sec_idx": 4, "dur_ratio": 0.34,
            "desc": "Karya seni filosofis tentang ketajaman pikiran manusia vs mesin",
            "query": "philosophical sculpture human mind consciousness silhouette",
            "fallbacks": ["rodin thinker sculpture classical contemplative art", "human consciousness art light"],
            "overlay": "Ketajaman Nalar Biologis", "metaphor": "Keunikan manusia",
        },
        {
            "sec_idx": 5, "dur_ratio": 0.5,
            "desc": "Seseorang duduk tenang melamun memandang pepohonan di luar tanpa gawai",
            "query": "person sitting quiet looking out window daydreaming calm",
            "fallbacks": ["peaceful contemplative person gazing window no phone", "tranquil moment window thinking"],
            "overlay": "Melamun 10 Menit Penuh", "metaphor": "Ruang hening",
        },
        {
            "sec_idx": 5, "dur_ratio": 0.5,
            "desc": "Sinar mentari pagi menyinari secangkir teh dan ruangan yang damai",
            "query": "morning sunlight warm peaceful living room cup steam",
            "fallbacks": ["tranquil sunlight room quiet morning stillness", "peaceful morning stillness sunlight"],
            "overlay": "Biarkan Pikiran Bernapas", "metaphor": "Bernapas sendiri",
        },
    ],
    5: [  # FUTURE × PROPERTY × HUMAN: Kenapa Tanah Makin Mahal Justru Saat Dunia Makin Virtual?
        {
            "sec_idx": 1, "dur_ratio": 1.0,
            "desc": "Hamparan tanah perkebunan luas diakuisisi dengan latar perbukitan hijau",
            "query": "vast agricultural farmland hills aerial landscape acquisition",
            "fallbacks": ["large private ranch landscape green pasture aerial", "vast rural estate farmland landscape"],
            "overlay": "Borong Ribuan Hektar Tanah", "metaphor": "Aset fisik nyata",
        },
        {
            "sec_idx": 2, "dur_ratio": 0.5,
            "desc": "Seseorang memakai kacamata VR headset di ruangan futuristik gelap",
            "query": "person wearing virtual reality headset metaverse cyberspace",
            "fallbacks": ["vr headset user immersive virtual world glowing", "virtual reality metaverse experience"],
            "overlay": "Dunia Virtual & Metaverse", "metaphor": "Dunia buatan",
        },
        {
            "sec_idx": 2, "dur_ratio": 0.5,
            "desc": "Mata air alami yang jernih dan hutan hijau asri yang murni",
            "query": "fresh clean natural spring water stream pristine forest",
            "fallbacks": ["pure mountain spring water pristine nature green", "crystal clear river forest wild"],
            "overlay": "Air Bersih & Alam Nyata", "metaphor": "Aset paling kuno",
        },
        {
            "sec_idx": 3, "dur_ratio": 0.33,
            "desc": "Penggandaan file digital tak terhingga dengan kecepatan nol biaya",
            "query": "infinite digital files duplication data copy abstract concept",
            "fallbacks": ["digital data replication screen zero cost abstract", "endless file icons copy digital"],
            "overlay": "Hukum Kelangkaan", "metaphor": "Kelimpahan digital",
        },
        {
            "sec_idx": 3, "dur_ratio": 0.33,
            "desc": "Grafik ekonomi tentang devaluasi nilai barang yang melimpah",
            "query": "financial market supply and demand price drop graph economic",
            "fallbacks": ["economic scarcity chart plummeting value digital", "supply demand curve graph"],
            "overlay": "Makin Melimpah Makin Anjlok", "metaphor": "Devaluasi nilai",
        },
        {
            "sec_idx": 3, "dur_ratio": 0.34,
            "desc": "Fasilitas server AI berkapasitas raksasa dengan kipas pendingin industri",
            "query": "hyperscale cloud server farm cooling industrial datacenter",
            "fallbacks": ["massive server racks datacenter artificial intelligence", "supercomputer facility hardware"],
            "overlay": "Server Tercanggih", "metaphor": "Mesin virtual",
        },
        {
            "sec_idx": 4, "dur_ratio": 0.33,
            "desc": "Segenggam tanah subur dipegang oleh tangan manusia di bawah sinar matahari",
            "query": "hands holding rich fertile soil earth sunlight agriculture",
            "fallbacks": ["human hands cupping soil garden sunbeam", "fertile earth in hands nature"],
            "overlay": "Sepetak Tanah Fisik", "metaphor": "Yang tak bisa digandakan",
        },
        {
            "sec_idx": 4, "dur_ratio": 0.33,
            "desc": "Pemandangan alam terbuka yang megah dengan udara segar bebas polusi",
            "query": "breathtaking majestic mountain valley open landscape sun",
            "fallbacks": ["wide open natural landscape mountains sunlight scenic", "panoramic nature valley untouched"],
            "overlay": "Barang Paling Mewah", "metaphor": "Kemewahan sejati",
        },
        {
            "sec_idx": 4, "dur_ratio": 0.34,
            "desc": "Ketenangan hutan pinus alami bermandikan cahaya matahari pagi",
            "query": "pine forest morning sunlight mist peaceful wilderness grove",
            "fallbacks": ["ancient forest trees sunbeams quiet nature", "peaceful woodland sun rays morning"],
            "overlay": "Keaslian Alam Nyata", "metaphor": "Kenyataan tak terbeli",
        },
        {
            "sec_idx": 5, "dur_ratio": 0.5,
            "desc": "Visual futuristik kecerdasan buatan dan otak digital gratis di internet",
            "query": "futuristic digital brain neural ai glow free download cyber",
            "fallbacks": ["artificial intelligence digital head download abstract", "cybernetic glowing brain concept"],
            "overlay": "Kecerdasan Bisa Didownload", "metaphor": "Masa depan komputasi",
        },
        {
            "sec_idx": 5, "dur_ratio": 0.5,
            "desc": "Orang tua dan anak berjalan di padang rumput hijau menatap matahari terbit",
            "query": "parent and child walking open green field sunrise nature",
            "fallbacks": ["family walking grassy hill sunrise future generations", "father child open landscape sunrise"],
            "overlay": "Warisan Paling Berharga?", "metaphor": "Warisan abadi",
        },
    ],
}


class VisualRequirementsGenerator:
    """Generates visual shot sequences for parsed narratives."""

    def generate_shots_for_narrative(
        self, narrative: NarasiScript
    ) -> List[VisualShotRequirement]:
        """
        Produce a list of VisualShotRequirement items for the given narrative.
        Uses the curated documentary shot designs if available, or falls back
        to intelligent automatic heuristic generation.
        """
        if narrative.index in _CURATED_NARRATIVE_SHOTS:
            return self._build_from_curated(narrative, _CURATED_NARRATIVE_SHOTS[narrative.index])
        return self._build_heuristic(narrative)

    def _build_from_curated(
        self, narrative: NarasiScript, shot_defs: List[Dict]
    ) -> List[VisualShotRequirement]:
        shots: List[VisualShotRequirement] = []
        # Group shot defs by section index
        by_sec: Dict[int, List[Dict]] = {}
        for sd in shot_defs:
            by_sec.setdefault(sd["sec_idx"], []).append(sd)

        shot_counter = 1
        for sec in narrative.sections:
            curated_list = by_sec.get(sec.index, [])
            if not curated_list:
                # generate heuristic fallback for this section
                sec_shots = self._build_section_heuristic(sec, narrative, shot_counter)
                shots.extend(sec_shots)
                shot_counter += len(sec_shots)
                continue

            # Calculate start/end times based on dur_ratio
            running_time = sec.start_seconds
            total_sec_dur = sec.duration_seconds

            for i, sd in enumerate(curated_list):
                shot_dur = total_sec_dur * sd.get("dur_ratio", 1.0 / len(curated_list))
                start_t = running_time
                end_t = min(sec.end_seconds, running_time + shot_dur)
                if i == len(curated_list) - 1:
                    end_t = sec.end_seconds  # Ensure exact fit

                shot_id = f"shot_{narrative.index:02d}_{shot_counter:02d}"
                shots.append(
                    VisualShotRequirement(
                        shot_id=shot_id,
                        section_index=sec.index,
                        section_name=sec.name,
                        section_type=sec.section_type,
                        start_seconds=start_t,
                        end_seconds=end_t,
                        duration_seconds=end_t - start_t,
                        visual_description=sd["desc"],
                        search_query=sd["query"],
                        fallback_queries=sd.get("fallbacks", []),
                        text_overlay=sd.get("overlay", ""),
                        preferred_media_type="any",
                        visual_metaphor=sd.get("metaphor", ""),
                    )
                )
                running_time = end_t
                shot_counter += 1

        return shots

    def _build_heuristic(self, narrative: NarasiScript) -> List[VisualShotRequirement]:
        shots: List[VisualShotRequirement] = []
        shot_counter = 1
        for sec in narrative.sections:
            sec_shots = self._build_section_heuristic(sec, narrative, shot_counter)
            shots.extend(sec_shots)
            shot_counter += len(sec_shots)
        return shots

    def _build_section_heuristic(
        self, sec: ScriptSection, narrative: NarasiScript, start_counter: int
    ) -> List[VisualShotRequirement]:
        # Determine number of sub-shots by duration:
        # <= 7s -> 1 shot
        # 8s - 15s -> 2 shots
        # 16s - 25s -> 3 shots
        # > 25s -> 4 shots
        if sec.duration_seconds <= 7.0:
            num_shots = 1
        elif sec.duration_seconds <= 15.0:
            num_shots = 2
        elif sec.duration_seconds <= 25.0:
            num_shots = 3
        else:
            num_shots = 4

        shot_dur = sec.duration_seconds / num_shots
        results: List[VisualShotRequirement] = []

        keywords = self._extract_keywords(sec.text)
        dna_theme = narrative.dna.lower()

        for i in range(num_shots):
            st = sec.start_seconds + i * shot_dur
            et = sec.end_seconds if i == num_shots - 1 else sec.start_seconds + (i + 1) * shot_dur
            shot_id = f"shot_{narrative.index:02d}_{start_counter + i:02d}"

            # Query selection based on section archetype
            if sec.section_type == "hook":
                q = f"{keywords[0] if keywords else 'modern workplace'} office documentary"
                overlay = "Perhatikan Ini"
            elif sec.section_type == "tension":
                q = f"busy pressure {keywords[1] if len(keywords) > 1 else 'technology machine'} fast"
                overlay = "Ada Yang Janggal"
            elif sec.section_type == "context":
                q = f"data charts {keywords[0] if keywords else 'research'} documents"
                overlay = "Fakta Di Lapangan"
            elif sec.section_type == "revelation":
                q = f"human silhouette {keywords[0] if keywords else 'thinking'} reflection"
                overlay = "Penyebab Sebenarnya"
            else:
                q = f"peaceful nature landscape sunlight contemplative"
                overlay = "Menurut Anda?"

            results.append(
                VisualShotRequirement(
                    shot_id=shot_id,
                    section_index=sec.index,
                    section_name=sec.name,
                    section_type=sec.section_type,
                    start_seconds=st,
                    end_seconds=et,
                    duration_seconds=et - st,
                    visual_description=f"Dokumenter visual {sec.section_type}: {q}",
                    search_query=q,
                    fallback_queries=[f"{dna_theme} documentary", "archival documentary footage"],
                    text_overlay=overlay,
                    preferred_media_type="any",
                    visual_metaphor=sec.section_type,
                )
            )

        return results

    def _extract_keywords(self, text: str) -> List[str]:
        words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
        stopwords = {
            "yang", "untuk", "dengan", "dalam", "bisa", "lebih", "kita", "karena",
            "sudah", "kalau", "nggak", "pada", "oleh", "dari", "akan", "kamu",
            "anda", "juga", "hanya", "mereka", "secara", "seperti", "sebenarnya"
        }
        filtered = [w for w in words if w not in stopwords]
        return filtered[:5] if filtered else ["workplace", "people"]
