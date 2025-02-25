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

available_languages = ["KO", "EN", "JA", "DE", "ZH", "ES", "FI", "FR", "IT", "PT", "RU"]
target_languages = ["EN", "JA", "DE", "ZH-HANT", "ZH-HANS", "ES", "FI", "FR", "IT", "PT-PT", "PT-BR", "RU", "KO"]
speaker_indices = [f"Speaker_0{i}" for i in range(5)]
voice_models = get_voice_list()

# Config 파일 로드를 위한 경로 추가
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

def update_dropdown(speaker_count):
    # Limit the choices to the first 'speaker_count' speakers.
    choices = speaker_indices[:speaker_count]
    default_value = choices[0] if choices else None
    return gr.Dropdown(choices=choices, value=default_value)

# 초기값이 아닌, 변경 시 업데이트될 값들을 저장하는 리스트
all_dropdowns = [""]

# 전역에 Dropdown 참조를 저장할 리스트
dd_list = []

def create_change_func(*dropdown_values):
    # 모든 Dropdown의 값을 다시 수집합니다.
    all_dropdowns.clear()
    for value in dropdown_values:
        if value:
            processed_value = value.split("(")[-1].rstrip(")").strip()
            all_dropdowns.append(processed_value)
    print(f"\033[92mUpdated dropdown values: {all_dropdowns}\033[0m")

# 슬라이더 값에 따라 미리 생성된 Dropdown의 표시 여부를 업데이트하는 함수
def update_dropdown_visibility(slider_value):
    updates = []
    for i in range(len(dd_list)):
        if i < slider_value:
            updates.append(gr.update(visible=True))
        else:
            updates.append(gr.update(visible=False))
    return updates


js = """
function playVideoSrtTime(srtTimeStr) {
  if (!srtTimeStr) {
    return;
  }

  const parts = srtTimeStr.split(/[:,]/);
  const hours = parseInt(parts[0], 10);
  const minutes = parseInt(parts[1], 10);
  const seconds = parseInt(parts[2], 10);
  const milliseconds = parseInt(parts[3], 10);

  const finalSeconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000;
  const video = document.querySelector('[data-testid="변환된 동영상-player"]');
  if (video) {
    video.currentTime = finalSeconds;
  } else {
    console.error("비디오 요소를 찾을 수 없습니다.");
  }
}
"""
def on_text_change(text):
    print(text)
    # 여기서는 단순히 입력값을 그대로 반환합니다.
    return text

with gr.Blocks(
    css_paths=CSS_PATH,
    js=js,
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

    # 미리 Dropdown에 들어갈 voice_choices 생성
    voice_choices = {f"{name} ({id})": id for id, name in voice_models.items()}

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
            with gr.Group():
                speaker_slider_state = gr.State(value=1)
                speaker_slider = gr.Slider(1, 5, value=1, label="화자 수", info="영상에 나오는 목소리 수", interactive=True, step=1)

                # 미리 최대 5개의 Dropdown을 생성하여 dd_container에 추가 (초기 slider 값은 1이므로 첫 번째만 보임)
                with gr.Column() as dd_container:
                    for i in range(5):
                        dd = gr.Dropdown(
                            label=f"Speaker_0{i}",
                            choices=list(voice_choices.keys()),
                            interactive=True,
                            visible=True if i < 1 else False
                        )
                        dd_list.append(dd)
                    # 각 Dropdown의 change 이벤트에 모든 Dropdown 값을 인자로 전달하도록 등록합니다.
                    for dd in dd_list:
                        dd.change(fn=create_change_func, inputs=dd_list)
                # 슬라이더 값 변경 시, 각 Dropdown의 표시 여부 업데이트
                speaker_slider.change(
                    fn=update_dropdown_visibility,
                    inputs=[speaker_slider],
                    outputs=dd_list
                )
            active_tab_state = gr.State(value="")
            with gr.Tab(label="유튜브 URL", id="url") as tab_url:
                input_url = gr.Textbox(
                    label="유튜브 URL",
                )

            with gr.Row():
                timestamp_start = gr.Textbox(
                    label="시작 - 종료 시간",
                    value="00:00:00",
                    placeholder="00:00:00",
                    max_length=8,
                    interactive=True,
                )
                timestamp_end = gr.Textbox(
                    elem_id="timestamp_end",
                    value=("00:00:30"),
                    max_length=8,
                    interactive=True,
                )

            tab_url.select(
                fn=lambda: selected_upload_method("url"),
                outputs=active_tab_state
            )
            start_btn = gr.Button("🔲 전체 시작")
            regenerate_video_btn = gr.Button("🔃 수정된 자막으로 재생성", interactive=False)

        with gr.Column(scale=3):
            output_video = gr.PlayableVideo(
                label="변환된 동영상",
                interactive=False,

            )
            with gr.Group():
                with gr.Row():
                    textbox_start = gr.Textbox(label="start", interactive=False, scale=1, placeholder="숫자 입력")
                    textbox_end = gr.Textbox(label="end", interactive=True, scale=1, placeholder="숫자 입력")
                    speaker_list = gr.Textbox(label="화자", interactive=True, scale=1, placeholder="SPEAKER_0n 입력")

                with gr.Row():
                    textbox_original = gr.Textbox(label="원본", interactive=True, placeholder="번역 전")
                    textbox_translation = gr.Textbox(label="번역", interactive=True, placeholder="번역 후")

                update_srt_btn = gr.Button("수정하기")

            srt_examples = gr.Examples(
                label="자막 (srt 파일)",
                examples_per_page=50,
                examples=[["00:00:00,000", "00:00:01,000", "SPEAKER_00", "예시", "example"]],
                inputs=[textbox_start, textbox_end, speaker_list, textbox_original, textbox_translation],
            )

            textbox_start.change(
                fn=on_text_change,
                inputs=textbox_start,
                outputs=usr_msg,
                js=js,
            )

        with gr.Column(scale=1):
            with gr.Group():
                gr.Label("⚙️ 제어판", show_label=False, elem_classes="header")
                # retranslate_btn = gr.Button("📝 번역 재시도", interactive=False)

                progress_label = gr.Textbox(label="진행 상황", interactive=False)

            d = gr.DownloadButton("변환된 영상 다운로드", visible=True, variant="primary", value="downloads/final_video.mp4")

    # <---------- 전체 시작 버튼 ---------->
    start_btn.click(
        lambda: gr.Button(interactive=False, value="🔳 전체 시작"),
        inputs=[],
        outputs=[start_btn]
    ).success(
        fn=lambda *args: process_video(
            args[0],  # input_url
            args[1],  # original_language
            args[2],  # target_language
            args[3],  # speaker_slider_state
            [x.split("(")[-1].rstrip(")").strip() for x in args[4:-2] if x],  # 드롭다운 값들 처리
            args[-2],  # timestamp_start
            args[-1]   # timestamp_end
        ),
        inputs=[input_url, original_language, target_language, speaker_slider_state, *dd_list, timestamp_start, timestamp_end],
        outputs=progress_label
    ).success(
        fn=lambda video_path: video_path,
        inputs=[progress_label],
        outputs=[output_video]
    ).success(
        fn=lambda: gr.update(value="downloads/final_video.mp4"), # Update download button value
        inputs=[],
        outputs=[d]
    ).success(
        fn=lambda: gr.Dataset(samples=parse_srt_files('downloads/transcription_refined.srt', 'downloads/translated.srt')),
        inputs=[],
        outputs=[srt_examples.dataset]
    ).success(
        fn=lambda: [gr.Button(interactive=True, value="🔲 전체 재시작"), gr.Button(interactive=True)],
        inputs=[],
        outputs=[start_btn, regenerate_video_btn]
    )
    # <---------- 자막 수정하기 버튼 ---------->
    update_srt_btn.click(
        fn=update_srt_dataset,
        inputs=[textbox_start, textbox_end, speaker_list, textbox_original, textbox_translation],
        outputs=[srt_examples.dataset, textbox_start, textbox_end, textbox_original, textbox_translation]
    )

    # <---------- 영상 재생성 버튼 ---------->
    regenerate_video_btn.click(
        fn=lambda *args: regenerate_video_from_srt(
            [x.split("(")[-1].rstrip(")").strip() for x in args if x]
        ),
        inputs=[*dd_list],
        outputs=[output_video]
    ).success(
        fn=lambda: gr.update(value="downloads/final_video.mp4"), # Update download button value
        inputs=[],
        outputs=[d]
    )

    speaker_slider.change(
        fn=lambda slider_value: slider_value,
        inputs=speaker_slider,
        outputs=speaker_slider_state
    )

if __name__ == "__main__":
    demo.launch()