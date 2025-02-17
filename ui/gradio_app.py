import gradio as gr
import os
import sys
import time

from ui.functions import get_voice_list
from ui.functions import selected_upload_method
from ui.functions import parse_srt_files
from ui.functions import write_srt_file
from ui.functions import remove_duplicate_start_times
from ui.functions import update_srt_dataset

from video_processing.downloader import download_youtube_video
from video_processing.trimmer import trim_video
from video_processing.audio_extractor import extract_audio_from_video
from video_processing.vocal_separation import separate_background_audio
from video_processing.transcription import transcribe_audio_whisper
from video_processing.srt_utils import create_srt
from video_processing.translation import translate_srt
from video_processing.tts import generate_tts_with_timestamps
from video_processing.merging import merge_audio_with_video, merge_background_with_tts
from video_processing.file_manager import get_file_path

from main import process_video
from main import regenerate_video_from_srt


CSS_PATH = "ui/style.css"

available_languages = ["KO"]
target_languages = ["EN", "JA", "ZH-HANT"]
voice_models = get_voice_list()

# Config 파일 로드를 위한 경로 추가
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

# <---------- GUI ---------->
with gr.Blocks(
    css_paths=CSS_PATH,
    theme=gr.themes.Soft(
        primary_hue=gr.themes.colors.neutral,
        secondary_hue=gr.themes.colors.amber,
        neutral_hue=gr.themes.colors.slate,
        font=["sans-serif"],
    ),
) as demo:
    gr.Markdown(
        '''
        # <center>Voice Builder<center>
        <center>한 번의 클릭으로 비디오를 번역 후 더빙 하세요.<center>
        <center>📁 비디오 포맷 업로드 or ▶️ 유튜브 URL 입력<center>
        '''
    )
    usr_msg = gr.State()
    with gr.Row():
        with gr.Column(scale=1):
            with gr.Row():
                original_language = gr.Dropdown(
                    label="원본 언어",
                    choices=available_languages,
                    value=available_languages[0],
                    interactive=True
                )
                target_language = gr.Dropdown(
                    label="대상 언어",
                    choices=target_languages,
                    value=target_languages[0],
                    interactive=True
                )
            with gr.Row():
                voice_choices = {f"{name} ({id})": id for id, name in voice_models.items()}
                selected_voice = gr.Dropdown(
                    label="음성 선택",
                    choices=list(voice_choices.keys()),
                    interactive=True
                )
            active_tab_state = gr.State(value="")
            with gr.Tab(label="유튜브 URL", id="url") as tab_url:
                input_url = gr.Textbox(
                    label="유튜브 URL",
                )
            with gr.Tab(label="동영상 업로드", id="file", interactive=False) as tab_file:
                input_video = gr.Video(
                    label="동영상 파일",
                )

            tab_file.select(
                fn=lambda: selected_upload_method("file"),
                outputs=active_tab_state
            )
            tab_url.select(
                fn=lambda: selected_upload_method("url"),
                outputs=active_tab_state
            )
            start_btn = gr.Button("🔲 전체 시작")
        with gr.Column(scale=3):
            output_video = gr.PlayableVideo(
                label="변환된 동영상",
                interactive=False
            )
            with gr.Group():
                with gr.Row():
                    textbox_start = gr.Textbox(label="start", interactive=True, placeholder="숫자 입력")
                    textbox_end = gr.Textbox(label="end", interactive=True, placeholder="숫자 입력")
                with gr.Row():
                    textbox_original = gr.Textbox(label="원본", interactive=True, placeholder="번역 전")
                    textbox_translation = gr.Textbox(label="번역", interactive=True, placeholder="번역 후")

                update_srt_btn = gr.Button("수정하기")


            srt_examples = gr.Examples(
                label="자막 (srt 파일)",
                examples_per_page=50,
                examples=[["00:00:00,000", "00:00:01,000", "예시", "example"]],
                inputs=[textbox_start, textbox_end, textbox_original, textbox_translation],
            )

        with gr.Column(scale=1):
            with gr.Group():
                gr.Label("⚙️ 제어판", show_label=False, elem_classes="header")
                retranslate_btn = gr.Button("📝 번역 재시도", interactive=False)
                regenerate_video_btn = gr.Button("🔃 영상 재생성", interactive=False)

                progress_label = gr.Textbox(label="진행 상황", interactive=False)

            d = gr.DownloadButton("변환된 영상 다운로드", visible=True, variant="primary", value="downloads/final_video.mp4")

    # <---------- 전체 시작 버튼 ---------->
    start_btn.click(
        lambda: gr.Button(interactive=False, value="🔳 전체 시작"),
        inputs=[],
        outputs=[start_btn]
    ).success(
        fn=lambda input_url, original_language, target_language, selected_voice: process_video(input_url, original_language, target_language, selected_voice.split("(")[-1].rstrip(")").strip()),
        inputs=[input_url, original_language, target_language, selected_voice],
        outputs=progress_label
    ).success(
        fn=lambda video_path: video_path,
        inputs=[progress_label],
        outputs=[output_video]
    ).success(
        fn=lambda: gr.Dataset(samples=parse_srt_files('downloads/transcription.srt', 'downloads/translated.srt')),
        inputs=[],
        outputs=[srt_examples.dataset]
    ).success(
        lambda: [gr.Button(interactive=True, value="🔲 전체 재시작"), gr.Button(interactive=True)],
        inputs=[],
        outputs=[start_btn, regenerate_video_btn]
    )

    # <---------- 자막 수정하기 버튼 ---------->
    update_srt_btn.click(
        fn=update_srt_dataset,
        inputs=[textbox_start, textbox_end, textbox_original, textbox_translation],
        outputs=[srt_examples.dataset, textbox_start, textbox_end, textbox_original, textbox_translation]
    )

    # <---------- 영상 재생성 버튼 ---------->
    regenerate_video_btn.click(
        fn=lambda selected_voice: regenerate_video_from_srt(selected_voice.split("(")[-1].rstrip(")").strip()),
        inputs=[selected_voice],
        outputs=[output_video]
    )

if __name__ == "__main__":
    demo.launch()
