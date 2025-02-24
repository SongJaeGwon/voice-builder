# voice-builder

### Requirements

```shell
$ brew install pipenv
$ pipenv install
$ pipenv shell
```

### Usage

- To test with CLI (predefined settings)
  - video_url = "https://www.youtube.com/watch?v=hSWsDc0h5g8" # 로컬 파일 경로 또는 다운로드 URL
  - source_lang = "KO" # 원본파일 언어
  - target_lang = "EN" # 번역할 언어
  - voice_id = "ir1CeAgkMhxW2txdJpxQ" # 일레븐랩스 보이스 id

```shell
$ python -m main
```

- Open Gradio web UI

```shell
$ python -m ui.gradio_app
```

Then go to the URL http://127.0.0.1:7860

#### Development

To develop Gradio UI, you need to set environment variable.

```shell
$ cd ./voice-builder
$ export PYTHONPATH=$(pwd)
```
