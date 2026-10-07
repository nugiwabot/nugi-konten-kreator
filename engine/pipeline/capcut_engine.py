"""
engine/pipeline/capcut_engine.py
================================
Native CapCut Desktop Draft Generation and Packaging Engine.
Location: engine/pipeline/capcut_engine.py

Primary NLE target for Nugi Konten Kreator.
Produces 100% compliant CapCut Desktop projects (versions 9.x - 10.x+ on Windows)
without any external API server or third-party cloud dependency.

Supports TWO production modes:
  1. Faceless Documentary Mode:
     - Track 0: Sequence of B-roll video/image clips timed to the spoken narrative
     - Track 1: Kinetic titles / motion graphics overlays
     - Track 2: High-contrast synchronized subtitle text track
     - Track 3: Background audio / music track

  2. Talking-Head + B-roll Mode:
     - Track 0: Main talking head raw footage (continuous time authority)
     - Track 1: Cutaway B-roll overlays
     - Track 2: Synchronized subtitle text track
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from engine.pipeline.timeline_model import MusicTrack, SubtitleCue, TimelineClip, TimelineData

logger = logging.getLogger("capcut_engine")


def detect_capcut_environment(custom_draft_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Dynamically inspects the user's Windows environment for CapCut Desktop.
    Never hardcodes usernames or paths.
    """
    local_app_data = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/AppData/Local")
    capcut_base = Path(local_app_data) / "CapCut"

    draft_root = None
    if custom_draft_dir:
        c_path = Path(custom_draft_dir)
        if c_path.is_dir():
            draft_root = c_path

    if draft_root is None:
        standard_draft = capcut_base / "User Data" / "Projects" / "com.lveditor.draft"
        if standard_draft.is_dir():
            draft_root = standard_draft

    apps_dir = capcut_base / "Apps"
    installed_version = "9.5.0"
    font_path = ""

    if apps_dir.is_dir():
        vers = [d for d in apps_dir.iterdir() if d.is_dir() and re.match(r"^\d+\.\d+\.\d+", d.name)]
        if vers:
            vers.sort(key=lambda x: [int(p) for p in re.findall(r"\d+", x.name)], reverse=True)
            installed_version = vers[0].name

        for root, _, files in os.walk(str(apps_dir)):
            for f in files:
                if f.lower() in ["en.ttf", "notosans-regular.ttf", "arial.ttf"]:
                    font_path = os.path.join(root, f).replace("\\", "/")
                    break
            if font_path:
                break

    if not font_path or not os.path.exists(font_path):
        font_path = "C:/Windows/Fonts/arial.ttf"

    return {
        "installed": draft_root is not None,
        "draft_root": draft_root,
        "capcut_base": capcut_base,
        "version": installed_version,
        "font_path": font_path,
    }


class CapCutDraftGenerator:
    """Generates complete, verified native CapCut Desktop Draft folder structures."""

    def __init__(self, capcut_env: Optional[Dict[str, Any]] = None):
        self.env = capcut_env or detect_capcut_environment()

    def generate_from_timeline(
        self,
        timeline: TimelineData,
        output_draft_dir: Path | str,
        project_name: Optional[str] = None,
        include_subtitles: bool = True,
    ) -> Path:
        """
        Generates a native CapCut Draft folder from a TimelineData specification.
        Handles both multi-clip sequences and multi-track overlays.
        """
        out_dir = Path(output_draft_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        for sub in [
            "adjust_mask", "common_attachment", "matting", "qr_upload",
            "Resources", "smart_crop", "subdraft", "Timelines"
        ]:
            (out_dir / sub).mkdir(parents=True, exist_ok=True)

        proj_name = project_name or timeline.project_name or "video_auto_capcut"
        now_ts = int(time.time())
        now_us = int(time.time() * 1_000_000)
        draft_id = str(uuid.uuid4()).upper()

        vid_w = timeline.width
        vid_h = timeline.height
        total_us = int(round(timeline.total_duration_seconds * 1_000_000))
        if total_us <= 0 and timeline.clips:
            max_end = max(c.end_seconds for c in timeline.clips)
            total_us = int(round(max_end * 1_000_000))

        font_path = self.env.get("font_path", "C:/Windows/Fonts/arial.ttf")

        # 1. Materials registration
        materials_videos: List[Dict[str, Any]] = []
        materials_texts: List[Dict[str, Any]] = []
        materials_audios: List[Dict[str, Any]] = []
        material_animations: List[Dict[str, Any]] = []
        canvases: List[Dict[str, Any]] = []
        speeds: List[Dict[str, Any]] = []
        placeholder_infos: List[Dict[str, Any]] = []
        sound_channel_mappings: List[Dict[str, Any]] = []
        vocal_separations: List[Dict[str, Any]] = []
        material_colors: List[Dict[str, Any]] = []

        path_to_mat_id: Dict[str, str] = {}

        def _get_or_create_media_mat(file_path: str, media_type: str, duration_us: int) -> str:
            resolved_slash = str(Path(file_path).resolve()).replace("\\", "/")
            if resolved_slash in path_to_mat_id:
                return path_to_mat_id[resolved_slash]

            m_id = str(uuid.uuid4()).upper()
            path_to_mat_id[resolved_slash] = m_id

            if media_type in ("video", "image"):
                materials_videos.append({
                    "id": m_id,
                    "unique_id": uuid.uuid4().hex,
                    "type": media_type,
                    "duration": duration_us,
                    "path": resolved_slash,
                    "media_path": "",
                    "local_id": "",
                    "has_audio": media_type == "video",
                    "reverse_path": "",
                    "intensifies_path": "",
                    "reverse_intensifies_path": "",
                    "intensifies_audio_path": "",
                    "cartoon_path": "",
                    "width": vid_w,
                    "height": vid_h,
                    "category_id": "",
                    "category_name": "local",
                    "material_id": "",
                    "material_name": Path(file_path).name,
                    "create_time": now_ts,
                    "origin_material_id": "",
                    "ai_matting": None,
                    "audio_fade": None,
                    "formula_id": "",
                    "freeze": None,
                    "gameplay": None,
                    "has_sound": media_type == "video",
                    "initial_scale": 1.0,
                    "is_ai_generate_content": False,
                    "is_unified_beauty_mode": False,
                    "local_material_id": "",
                    "multi_language_current": "none",
                    "sound_channel_mapping": None,
                    "source": 0,
                    "source_platform": 0,
                    "stable": None,
                    "video_algorithm": {
                        "algorithms": [],
                        "deflicker": None,
                        "motion_blur_info": None,
                        "noise_reduction": None,
                        "path": "",
                        "quality_enhance": None,
                        "time_range": None
                    }
                })
            return m_id

        def make_aux_refs() -> List[str]:
            cid = str(uuid.uuid4()).upper()
            canvases.append({
                "album_image": "", "blur": 0.0, "color": "",
                "id": cid, "image": "", "image_id": "", "image_name": "",
                "source_platform": 0, "team_id": "", "type": "canvas_color"
            })
            spid = str(uuid.uuid4()).upper()
            speeds.append({
                "curve_speed": None, "id": spid, "mode": 0,
                "speed": 1.0, "type": "speed"
            })
            pid = str(uuid.uuid4()).upper()
            placeholder_infos.append({
                "id": pid, "is_placeholder": False, "type": "placeholder_info"
            })
            scmid = str(uuid.uuid4()).upper()
            sound_channel_mappings.append({
                "audio_channel_mapping": 0, "id": scmid, "is_config_open": False, "type": ""
            })
            vsid = str(uuid.uuid4()).upper()
            vocal_separations.append({
                "choice": 0, "id": vsid, "production_path": "", "time_range": None, "type": "vocal_separation"
            })
            mcid = str(uuid.uuid4()).upper()
            material_colors.append({
                "id": mcid, "type": "material_color", "color": [0.0, 0.0, 0.0, 1.0]
            })
            return [cid, spid, pid, scmid, vsid, mcid]

        # 2. Build Tracks
        track_0_segments: List[Dict[str, Any]] = []
        track_1_segments: List[Dict[str, Any]] = []

        # Sort clips by timeline start
        sorted_clips = sorted(timeline.clips, key=lambda c: c.start_seconds)

        for clip in sorted_clips:
            c_path = clip.file_path
            if not c_path or not Path(c_path).exists():
                logger.warning(f"Clip file not found: {c_path}. Skipping.")
                continue

            c_dur_us = int(round(clip.duration_seconds * 1_000_000))
            if c_dur_us <= 0:
                continue

            mat_id = _get_or_create_media_mat(c_path, clip.media_type, c_dur_us)
            st_us = int(round(clip.start_seconds * 1_000_000))
            trim_in_us = int(round(clip.source_start * 1_000_000))

            seg_payload = {
                "id": str(uuid.uuid4()).upper(),
                "source_timerange": {"start": trim_in_us, "duration": c_dur_us},
                "target_timerange": {"start": st_us, "duration": c_dur_us},
                "render_timerange": {"start": 0, "duration": 0},
                "desc": clip.text_overlay or clip.asset_title,
                "state": 0,
                "speed": 1.0,
                "is_loop": False,
                "is_tone_modify": False,
                "reverse": False,
                "intensifies_audio": False,
                "cartoon": False,
                "volume": clip.volume if clip.media_type == "video" else 0.0,
                "last_nonzero_volume": 1.0,
                "clip": {
                    "scale": {"x": clip.scale_x, "y": clip.scale_y},
                    "rotation": 0.0,
                    "transform": {"x": clip.transform_x, "y": clip.transform_y},
                    "flip": {"vertical": False, "horizontal": False},
                    "alpha": 1.0
                },
                "uniform_scale": {"on": True, "value": 1.0},
                "material_id": mat_id,
                "extra_material_refs": make_aux_refs(),
                "render_index": 0 if clip.track == 0 else 1,
                "keyframe_refs": [],
                "enable_lut": True,
                "enable_adjust": True,
                "enable_hsl": False,
                "visible": True,
                "group_id": "",
                "enable_color_curves": True,
                "enable_hsl_curves": True,
                "track_render_index": clip.track,
                "hdr_settings": {"mode": 1, "intensity": 1.0, "nits": 1000},
                "enable_color_wheels": True,
                "track_attribute": 0,
                "is_placeholder": False,
                "template_id": "",
                "enable_smart_color_adjust": False,
                "template_scene": "default",
                "common_keyframes": [],
                "caption_info": None,
                "responsive_layout": {"enable": False, "target_follow": "", "size_layout": 0, "horizontal_pos_layout": 0, "vertical_pos_layout": 0},
                "enable_color_match_adjust": False,
                "enable_color_correct_adjust": False,
                "enable_adjust_mask": False,
                "raw_segment_id": "",
                "lyric_keyframes": None,
                "enable_video_mask": True,
                "digital_human_template_group_id": "",
                "color_correct_alg_result": "",
                "source": "segmentsourcenormal",
                "enable_mask_stroke": False,
                "enable_mask_shadow": False,
                "enable_color_adjust_pro": False,
                "segment_color_tag": ""
            }

            if clip.track == 0:
                track_0_segments.append(seg_payload)
            else:
                track_1_segments.append(seg_payload)

        tracks: List[Dict[str, Any]] = []

        # Video Track 0 (Main Video)
        tracks.append({
            "id": str(uuid.uuid4()).upper(),
            "type": "video",
            "flag": 0,
            "attribute": 0,
            "segments": track_0_segments
        })

        # Video Track 1 (Overlay B-roll) if any
        if track_1_segments:
            tracks.append({
                "id": str(uuid.uuid4()).upper(),
                "type": "video",
                "flag": 2,  # Flag 2 = PIP / Overlay
                "attribute": 0,
                "segments": track_1_segments
            })

        # Subtitle Text Track
        if include_subtitles and timeline.subtitles:
            track_sub_segments: List[Dict[str, Any]] = []
            for sub in timeline.subtitles:
                s_dur_us = int(round(sub.duration_seconds * 1_000_000))
                if s_dur_us <= 0:
                    continue
                s_st_us = int(round(sub.start_seconds * 1_000_000))

                txt_mat_id = str(uuid.uuid4()).upper()
                anim_id = str(uuid.uuid4()).upper()
                material_animations.append({
                    "id": anim_id,
                    "type": "sticker_animation",
                    "animations": [],
                    "multi_language_current": "none"
                })

                text_obj = {
                    "text": sub.text,
                    "styles": [
                        {
                            "fill": {
                                "content": {
                                    "render_type": "solid",
                                    "solid": {"color": [1.0, 1.0, 1.0]}  # High contrast white
                                }
                            },
                            "font": {
                                "path": font_path,
                                "id": ""
                            },
                            "size": 11.0,
                            "bold": True,
                            "useLetterColor": True,
                            "strokes": [
                                {
                                    "alpha": 1.0,
                                    "content": {
                                        "render_type": "solid",
                                        "solid": {"color": [0.0, 0.0, 0.0]}  # Black outline
                                    },
                                    "width": 0.06
                                }
                            ],
                            "range": [0, len(sub.text)]
                        }
                    ]
                }

                materials_texts.append({
                    "recognize_task_id": "",
                    "id": txt_mat_id,
                    "name": "",
                    "recognize_text": "",
                    "recognize_model": "",
                    "punc_model": "",
                    "type": "text",
                    "content": json.dumps(text_obj, ensure_ascii=False),
                    "base_content": "",
                    "words": {"start_time": [], "end_time": [], "text": []},
                    "current_words": {"start_time": [], "end_time": [], "text": []},
                    "global_alpha": 1.0,
                    "combo_info": {"text_templates": []},
                    "caption_template_info": {"resource_id": "", "third_resource_id": "", "resource_name": "", "category_id": "", "category_name": "", "effect_id": "", "request_id": "", "path": "", "is_new": False, "source_platform": 0},
                    "layer_weight": 1,
                    "letter_spacing": 0.0,
                    "text_curve": None,
                    "text_loop_on_path": False,
                    "offset_on_path": 0.0,
                    "enable_path_typesetting": False,
                    "text_exceeds_path_process_type": 0,
                    "text_typesetting_paths": None,
                    "add_type": 0,
                    "operation_type": 0,
                    "recognize_type": 0,
                    "fonts": [],
                    "background_color": "",
                    "background_alpha": 0.0,
                    "background_style": 0,
                    "background_round_radius": 0.0,
                    "background_width": 0.0,
                    "background_height": 0.0,
                    "background_vertical_offset": 0.0,
                    "background_horizontal_offset": 0.0,
                    "background_fill": "",
                    "single_char_bg_enable": False,
                    "single_char_bg_color": "",
                    "single_char_bg_alpha": 1.0,
                    "single_char_bg_round_radius": 0.3,
                    "single_char_bg_width": 0.0,
                    "single_char_bg_height": 0.0,
                    "single_char_bg_vertical_offset": 0.0,
                    "single_char_bg_horizontal_offset": 0.0,
                    "font_team_id": "",
                    "tts_auto_update": False,
                    "text_preset_resource_id": "",
                    "group_id": "",
                    "preset_id": "",
                    "preset_name": "",
                    "preset_category": "",
                    "preset_category_id": "",
                    "preset_index": 0,
                    "preset_has_set_alignment": False,
                    "force_apply_line_max_width": False,
                    "language": "",
                    "relevance_segment": [],
                    "original_size": [],
                    "fixed_width": -1.0,
                    "fixed_height": -1.0,
                    "autoAdaptCanvasEnabled": False,
                    "line_max_width": 0.82,
                    "oneline_cutoff": False,
                    "cutoff_postfix": "",
                    "subtitle_template_original_fontsize": 0.0,
                    "subtitle_keywords": None,
                    "inner_padding": -1.0,
                    "multi_language_current": "none",
                    "source_from": "",
                    "is_lyric_effect": False,
                    "lyric_group_id": "",
                    "lyrics_template": {"resource_id": "", "resource_name": "", "panel": "", "effect_id": "", "path": "", "category_id": "", "category_name": "", "request_id": ""},
                    "is_batch_replace": False,
                    "is_words_linear": False,
                    "ssml_content": "",
                    "subtitle_keywords_config": None,
                    "sub_template_id": -1,
                    "translate_original_text": ""
                })

                track_sub_segments.append({
                    "id": str(uuid.uuid4()).upper(),
                    "source_timerange": None,
                    "target_timerange": {"start": s_st_us, "duration": s_dur_us},
                    "render_timerange": {"start": 0, "duration": 0},
                    "desc": "",
                    "state": 0,
                    "speed": 1.0,
                    "is_loop": False,
                    "is_tone_modify": False,
                    "reverse": False,
                    "intensifies_audio": False,
                    "cartoon": False,
                    "volume": 1.0,
                    "last_nonzero_volume": 1.0,
                    "clip": {
                        "scale": {"x": 1.0, "y": 1.0},
                        "rotation": 0.0,
                        "transform": {"x": 0.0, "y": -0.75},  # Bottom third placement
                        "flip": {"vertical": False, "horizontal": False},
                        "alpha": 1.0
                    },
                    "uniform_scale": {"on": True, "value": 1.0},
                    "material_id": txt_mat_id,
                    "extra_material_refs": [anim_id],
                    "render_index": 14000,
                    "keyframe_refs": [],
                    "enable_lut": False,
                    "enable_adjust": False,
                    "enable_hsl": False,
                    "visible": True,
                    "group_id": "",
                    "enable_color_curves": True,
                    "enable_hsl_curves": True,
                    "track_render_index": 2,
                    "hdr_settings": None,
                    "enable_color_wheels": True,
                    "track_attribute": 0,
                    "is_placeholder": False,
                    "template_id": "",
                    "enable_smart_color_adjust": False,
                    "template_scene": "default",
                    "common_keyframes": [],
                    "caption_info": None,
                    "responsive_layout": {"enable": False, "target_follow": "", "size_layout": 0, "horizontal_pos_layout": 0, "vertical_pos_layout": 0},
                    "enable_color_match_adjust": False,
                    "enable_color_correct_adjust": False,
                    "enable_adjust_mask": False,
                    "raw_segment_id": "",
                    "lyric_keyframes": None,
                    "enable_video_mask": True,
                    "digital_human_template_group_id": "",
                    "color_correct_alg_result": "",
                    "source": "segmentsourcenormal",
                    "enable_mask_stroke": False,
                    "enable_mask_shadow": False,
                    "enable_color_adjust_pro": False,
                    "segment_color_tag": ""
                })

            tracks.append({
                "id": str(uuid.uuid4()).upper(),
                "type": "text",
                "flag": 0,
                "attribute": 0,
                "segments": track_sub_segments
            })

        # Assemble full materials structure
        all_materials = {
            "flowers": [],
            "videos": materials_videos,
            "tail_leaders": [],
            "audios": materials_audios,
            "images": [],
            "texts": materials_texts,
            "effects": [],
            "stickers": [],
            "canvases": canvases,
            "transitions": [],
            "audio_effects": [],
            "audio_fades": [],
            "beats": [],
            "material_animations": material_animations,
            "placeholders": [],
            "placeholder_infos": placeholder_infos,
            "speeds": speeds,
            "common_mask": [],
            "chromas": [],
            "text_templates": [],
            "realtime_denoises": [],
            "audio_pannings": [],
            "audio_pitch_shifts": [],
            "video_trackings": [],
            "hsl": [],
            "drafts": [],
            "color_curves": [],
            "hsl_curves": [],
            "primary_color_wheels": [],
            "log_color_wheels": [],
            "video_effects": [],
            "ai_text_effects": [],
            "audio_balances": [],
            "handwrites": [],
            "manual_deformations": [],
            "manual_beautys": [],
            "plugin_effects": [],
            "sound_channel_mappings": sound_channel_mappings,
            "green_screens": [],
            "shapes": [],
            "material_colors": material_colors,
            "digital_humans": [],
            "digital_human_model_dressing": [],
            "smart_crops": [],
            "ai_translates": [],
            "audio_track_indexes": [],
            "loudnesses": [],
            "vocal_beautifys": [],
            "vocal_separations": vocal_separations,
            "smart_relights": [],
            "time_marks": [],
            "multi_language_refs": [],
            "video_shadows": [],
            "video_strokes": [],
            "video_radius": []
        }

        # 3. draft_content.json
        draft_content = {
            "id": draft_id,
            "version": 360000,
            "new_version": "183.0.0",
            "name": proj_name,
            "duration": total_us,
            "create_time": now_ts,
            "update_time": now_ts,
            "fps": timeline.fps,
            "is_drop_frame_timecode": False,
            "color_space": 0,
            "config": {
                "adjust_max_index": 1,
                "attachment_info": [],
                "combination_max_index": 1,
                "export_range": None,
                "extract_audio_last_index": 1,
                "lyrics_recognition_id": "",
                "lyrics_sync": True,
                "lyrics_task_id": "",
                "maintrack_adsorb": True,
                "material_save_mode": 0,
                "multi_language_current": "none",
                "multi_language_list": [],
                "multi_language_main": "none",
                "multi_language_mode": "none",
                "original_sound_last_index": 1,
                "record_audio_last_index": 1,
                "sticker_max_index": 1,
                "subtitle_recognition_id": "",
                "subtitle_sync": True,
                "subtitle_task_id": "",
                "system_font_list": [],
                "video_mute": False,
                "zoom_info_params": None
            },
            "canvas_config": {
                "width": vid_w,
                "height": vid_h,
                "ratio": timeline.aspect_ratio
            },
            "materials": all_materials,
            "tracks": tracks
        }

        content_file = out_dir / "draft_content.json"
        content_file.write_text(json.dumps(draft_content, ensure_ascii=False, indent=2), encoding="utf-8")
        shutil.copyfile(content_file, out_dir / "draft_content.json.bak")

        # 4. draft_meta_info.json
        draft_fold_str = str(out_dir.resolve()).replace("\\", "/")
        draft_root_str = str(out_dir.parent.resolve()).replace("\\", "/")

        draft_meta = {
            "cloud_draft_cover": False,
            "cloud_draft_sync": False,
            "cloud_package_completed_time": "",
            "draft_cloud_capcut_purchase_info": "",
            "draft_cloud_last_action_download": False,
            "draft_cloud_package_type": "",
            "draft_cloud_purchase_info": "",
            "draft_cloud_template_id": "",
            "draft_cloud_tutorial_info": "",
            "draft_cloud_videocut_purchase_info": "",
            "draft_cover": "draft_cover.jpg",
            "draft_deeplink_url": "",
            "draft_enterprise_info": {"draft_enterprise_extra": "", "draft_enterprise_id": "", "draft_enterprise_name": "", "enterprise_material": []},
            "draft_fold_path": draft_fold_str,
            "draft_id": draft_id,
            "draft_is_ae_produce": False,
            "draft_is_ai_packaging_used": False,
            "draft_is_ai_shorts": False,
            "draft_is_ai_translate": False,
            "draft_is_article_video_draft": False,
            "draft_is_cloud_temp_draft": False,
            "draft_is_from_deeplink": False,
            "draft_is_infinite_canvas_draft": False,
            "draft_is_invisible": False,
            "draft_is_pippit_draft": False,
            "draft_is_web_article_video": False,
            "draft_materials": [
                {"type": 0, "value": [v["path"] for v in materials_videos]},
                {"type": 1, "value": []},
                {"type": 2, "value": []},
                {"type": 3, "value": []},
                {"type": 6, "value": []},
                {"type": 7, "value": []},
                {"type": 8, "value": []}
            ],
            "draft_materials_copied_info": [],
            "draft_name": proj_name,
            "draft_need_rename_folder": False,
            "draft_new_version": "",
            "draft_removable_storage_device": "",
            "draft_root_path": draft_root_str,
            "draft_segment_extra_info": [],
            "draft_timeline_materials_size_": 1024,
            "draft_type": "",
            "draft_web_article_video_enter_from": "",
            "pippit_avatar_url": "",
            "pippit_extra_info": "",
            "pippit_id": "",
            "pippit_user_name": "",
            "tm_draft_cloud_completed": "",
            "tm_draft_cloud_entry_id": -1,
            "tm_draft_cloud_modified": 0,
            "tm_draft_cloud_parent_entry_id": -1,
            "tm_draft_cloud_space_id": -1,
            "tm_draft_cloud_user_id": -1,
            "tm_draft_create": now_us,
            "tm_draft_modified": now_us,
            "tm_draft_removed": 0,
            "tm_duration": total_us
        }

        meta_file = out_dir / "draft_meta_info.json"
        meta_file.write_text(json.dumps(draft_meta, ensure_ascii=False, indent=2), encoding="utf-8")

        # 5. Auxiliary configuration files
        (out_dir / "draft_settings").write_text(
            f"[General]\r\ndraft_create_time={now_ts}\r\ndraft_last_edit_time={now_ts}\r\nreal_edit_seconds=0\r\nreal_edit_keys=0\r\ncloud_last_modify_platform=windows\r\n",
            encoding="utf-8"
        )
        t_id = str(uuid.uuid4()).upper()
        (out_dir / "timeline_layout.json").write_text(
            json.dumps({"dockItems": [{"dockIndex": 0, "ratio": 1, "timelineIds": [t_id], "timelineNames": ["Timeline 01"]}], "layoutOrientation": 1}),
            encoding="utf-8"
        )
        (out_dir / "draft_agency_config.json").write_text(
            json.dumps({"is_auto_agency_enabled": False, "is_auto_agency_popup": False, "is_single_agency_mode": False, "marterials": None, "use_converter": False, "video_resolution": 720}),
            encoding="utf-8"
        )
        (out_dir / "draft_biz_config.json").write_text("", encoding="utf-8")
        (out_dir / "draft_virtual_store.json").write_text(
            json.dumps({"draft_materials": [], "draft_virtual_store": []}),
            encoding="utf-8"
        )
        (out_dir / "key_value.json").write_text("{}", encoding="utf-8")
        (out_dir / "performance_opt_info.json").write_text(
            json.dumps({"manual_cancle_precombine_segs": None, "need_auto_precombine_segs": None}),
            encoding="utf-8"
        )
        (out_dir / "attachment_pc_common.json").write_text(
            json.dumps({
                "ai_packaging_infos": [],
                "ai_packaging_report_info": {"caption_id_list": [], "commercial_material": "", "material_source": "", "method": "", "page_from": "", "style": "", "task_id": "", "text_style": "", "tos_id": "", "video_category": ""},
                "broll": {"ai_packaging_infos": [], "ai_packaging_report_info": {"caption_id_list": [], "commercial_material": "", "material_source": "", "method": "", "page_from": "", "style": "", "task_id": "", "text_style": "", "tos_id": "", "video_category": ""}},
                "commercial_music_category_ids": [],
                "pc_feature_flag": 0,
                "recognize_tasks": [],
                "reference_lines_config": {"horizontal_lines": [], "is_lock": False, "is_visible": False, "vertical_lines": []},
                "safe_area_type": 0,
                "template_item_infos": [],
                "unlock_template_ids": []
            }),
            encoding="utf-8"
        )

        logger.info(
            f"CapCut Desktop Draft generated: {out_dir} | "
            f"Tracks: {len(tracks)} (Track 0: {len(track_0_segments)}, Track 1: {len(track_1_segments)}, Subtitles: {len(materials_texts)})"
        )
        return out_dir

    def install_to_capcut_desktop(
        self,
        draft_dir: Path | str,
        project_name: str,
        capcut_draft_root: Optional[Path | str] = None,
    ) -> Path:
        """
        Installs/copies the generated draft package to the user's CapCut Desktop drafts folder.
        Guarantees:
          - Never overwrites existing CapCut projects (generates unique folder name).
          - Backs up root_meta_info.json before modifying.
          - Registers project in root_meta_info.json.
        """
        draft_p = Path(draft_dir).resolve()
        draft_root = Path(capcut_draft_root) if capcut_draft_root else self.env.get("draft_root")

        if not draft_root or not Path(draft_root).is_dir():
            raise FileNotFoundError(
                "CapCut Desktop draft folder not found on this system.\n"
                "Please verify that CapCut Desktop is installed and opened once."
            )

        target_root = Path(draft_root)
        candidate_name = project_name
        counter = 1
        target_folder = target_root / candidate_name
        while target_folder.exists():
            counter += 1
            candidate_name = f"{project_name}_{counter:02d}"
            target_folder = target_root / candidate_name

        shutil.copytree(draft_p, target_folder)

        target_dir_slash = str(target_folder.resolve()).replace("\\", "/")
        capcut_root_slash = str(target_root.resolve()).replace("\\", "/")

        # Update metadata in destination
        meta_file = target_folder / "draft_meta_info.json"
        if meta_file.exists():
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
            unique_draft_id = str(uuid.uuid4()).upper()
            meta["draft_id"] = unique_draft_id
            meta["draft_fold_path"] = target_dir_slash
            meta["draft_root_path"] = capcut_root_slash
            meta["draft_name"] = candidate_name
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)

        content_file = target_folder / "draft_content.json"
        if content_file.exists():
            with open(content_file, "r", encoding="utf-8") as f:
                content = json.load(f)
            content["id"] = unique_draft_id
            content["name"] = candidate_name
            with open(content_file, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
            shutil.copyfile(content_file, target_folder / "draft_content.json.bak")

        # Update root_meta_info.json
        root_meta_file = target_root / "root_meta_info.json"
        if root_meta_file.exists():
            bak_file = target_root / "root_meta_info.json.bak"
            shutil.copyfile(root_meta_file, bak_file)

            with open(root_meta_file, "r", encoding="utf-8") as f:
                root_data = json.load(f)

            all_drafts = root_data.get("all_draft_store", [])
            all_drafts = [d for d in all_drafts if d.get("draft_id") != unique_draft_id and d.get("draft_name") != candidate_name]

            entry = {
                "cloud_draft_cover": False,
                "cloud_draft_sync": False,
                "draft_cloud_last_action_download": False,
                "draft_cloud_purchase_info": "",
                "draft_cloud_template_id": "",
                "draft_cloud_tutorial_info": "",
                "draft_cloud_videocut_purchase_info": "",
                "draft_cover": f"{target_dir_slash}\\draft_cover.jpg",
                "draft_fold_path": target_dir_slash,
                "draft_id": unique_draft_id,
                "draft_is_ai_shorts": False,
                "draft_is_cloud_temp_draft": False,
                "draft_is_infinite_canvas_draft": False,
                "draft_is_invisible": False,
                "draft_is_pippit_draft": False,
                "draft_is_web_article_video": False,
                "draft_name": candidate_name,
                "draft_new_version": "",
                "draft_root_path": capcut_root_slash,
                "draft_type": "",
                "draft_web_article_video_enter_from": "",
                "tm_draft_cloud_completed": "",
                "tm_draft_cloud_entry_id": -1,
                "tm_draft_cloud_modified": 0,
                "tm_draft_cloud_parent_entry_id": -1,
                "tm_draft_cloud_space_id": -1,
                "tm_draft_cloud_user_id": -1,
                "tm_draft_create": int(time.time() * 1_000_000),
                "tm_draft_modified": int(time.time() * 1_000_000),
                "tm_draft_removed": 0,
                "tm_duration": content.get("duration", 0)
            }
            all_drafts.append(entry)
            root_data["all_draft_store"] = all_drafts

            with open(root_meta_file, "w", encoding="utf-8") as f:
                json.dump(root_data, f, ensure_ascii=False, indent=2)

        logger.info(f"CapCut Draft installed to user library: '{candidate_name}' -> {target_folder}")
        return target_folder
