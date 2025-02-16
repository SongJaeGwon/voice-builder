import gradio as gr
from ui_functions import get_voice_list
from ui_functions import selected_upload_method

from video_processing.downloader import download_youtube_video

CSS_PATH = "ui/style.css"

available_languages = ["KO"]
target_languages = ["EN", "JA", "ZH-HANT"]
voice_models = get_voice_list()

def srt_builder():
    print('good!')

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
            convert_btn = gr.Button("🔘 변환 시작")
            # convert_btn.click(
            #     fn=lambda tab: f"{tab} 변환 중...",
            #     inputs=active_tab_state,
            #     outputs=convert_btn
            # )
            convert_btn.click(
                fn=lambda url: download_youtube_video(url),
                inputs=input_url,
            )
        with gr.Column(scale=3):
            output_video = gr.PlayableVideo(
                label="변환된 동영상",
                interactive=False
            )
            with gr.Group():
                with gr.Row():
                    textbox_start = gr.Textbox(label="start", placeholder="숫자 입력")
                    textbox_end = gr.Textbox(label="end", placeholder="숫자 입력")
                with gr.Row():
                    textbox_original = gr.Textbox(label="원본", placeholder="번역 전")
                    textbox_translation = gr.Textbox(label="번역", placeholder="번역 후")

                update_srt_btn = gr.Button("수정하기")


            examples = gr.Examples(
                examples=[
                    ["0", "1", "2test test test test test", "2test test test test test"],
                    ["1", "2", "2", "2"],
                    ["2", "3", "2.5", "2"],
                    ["3", "4", "1.2", "2"]
                ],
                inputs=[textbox_start, textbox_end, textbox_original, textbox_translation],
            )

        with gr.Column(scale=1):
            with gr.Group():
                gr.Label("⚙️ 제어판", show_label=False, elem_classes="header")
                retranslate_btn = gr.Button("다시 번역하기")

                final_btn = gr.Button("최종 영상 생성")
                progress_label = gr.Textbox(label="진행 상황")

            d = gr.DownloadButton("Download the file", visible=True, variant="primary")
    # with gr.Row():
        # progress_label.visible = True
        # progress_label.label = "진행 상황"
        # progress_label = gr.Textbox(label="진행 상황")


    # with gr.Row(elem_classes="col-container"):
    #     with gr.Column(elem_id="history"):
    #         with gr.Row():
    #             add_dialog = gr.ClearButton(
    #                 # components=[chat_his],
    #                 icon=r"icon\add_dialog.png",
    #                 #variant="primary",
    #                 # value=i18n("New Dialog"),
    #                 min_width=5,
    #                 elem_id="btn_transparent",
    #                 size="sm"
    #             )
    #             delete_dialog = gr.Button(
    #                 icon=r"icon\delete_dialog.png",
    #                 # value=i18n("Delete Dialog"),
    #                 min_width=5,
    #                 elem_id="btn_transparent",
    #                 size="sm",
    #             )

# <---------- 동영상 업로드 // 유튜브 URL Tab ---------->

if __name__ == "__main__":
    demo.launch()
