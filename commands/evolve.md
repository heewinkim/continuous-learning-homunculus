백그라운드에서 자동으로 쌓인 evolved 항목들을 보여주고, 내가 선택한 것만 실제 ~/.claude/에 적용해줘.

다음 단계로 진행해:

1. `python3 ~/.claude/skills/continuous-learning-homunculus/scripts/instinct-cli.py apply --list` 를 실행해서 현재 staged된 항목 목록을 보여줘

2. 각 항목의 이름과 내용을 간단히 요약해서 나에게 설명해줘. 아직 아무것도 적용하지 마.

3. 어떤 것을 실제로 적용할지 물어봐

4. 확인이 되면, 선택된 항목을 적용하려면 interactive 입력이 필요하므로 터미널에서 직접 실행하도록 안내해줘:
   ```
   python3 ~/.claude/skills/continuous-learning-homunculus/scripts/instinct-cli.py apply
   ```
   (각 항목마다 y/n으로 선택, --force로 이미 적용된 것도 재선택 가능)

staged 항목이 없으면 "아직 진화할 내용이 없어. 세션이 쌓이면 자동으로 생겨!" 라고 알려줘.
