"""
Game AI - API版本
使用外部大模型API进行游戏操作，本地OCR（pytesseract）识别屏幕文字。
支持经验总结与复用。
"""

import json
import time
import re
import sys
import os
import base64
import warnings
from pathlib import Path
from dataclasses import dataclass, asdict

warnings.filterwarnings("ignore")

# ============================================================
#  结构化输出定义
# ============================================================

@dataclass
class GameAction:
    """模型输出的标准动作格式"""
    action: str          # move / click / attack / use_item / wait / explore / custom
    target: str = ""     # enemy / door / npc / item
    direction: str = ""  # up / down / left / right
    position: str = ""   # x,y
    confidence: float = 0.0
    reasoning: str = ""
    raw_text: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class Experience:
    """经验记录"""
    id: int = 0
    timestamp: str = ""
    observation: str = ""
    action: str = ""
    result: str = ""
    lesson: str = ""


# ============================================================
#  简单本地 OCR（基于 pytesseract / easyocr fallback）
# ============================================================

class LocalOCR:
    """本地OCR：优先pytesseract，fallback到easyocr，都没有则提示"""

    def __init__(self, lang: str = "chi_sim+eng"):
        self.lang = lang
        self._backend = None
        self._engine = None

        # 尝试 pytesseract
        try:
            import pytesseract
            from PIL import Image
            self._engine = pytesseract
            self._Image = Image
            self._backend = "pytesseract"
            print("[OCR] pytesseract 加载成功")
            return
        except ImportError:
            pass

        # 尝试 easyocr
        try:
            import easyocr
            langs = ["ch_sim", "en"] if "chi" in lang else ["en"]
            self._engine = easyocr.Reader(langs, gpu=False)
            self._backend = "easyocr"
            print("[OCR] easyocr 加载成功")
            return
        except ImportError:
            pass

        print("[OCR] 警告: 无可用OCR引擎。请安装: pip install pytesseract Pillow 或 pip install easyocr")

    def recognize(self, image_path: str = None, image_bytes: bytes = None) -> str:
        if not self._backend:
            return "[OCR不可用] 请安装 pytesseract 或 easyocr"
        try:
            import io
            if self._backend == "pytesseract":
                if image_bytes:
                    img = self._Image.open(io.BytesIO(image_bytes))
                elif image_path:
                    img = self._Image.open(image_path)
                else:
                    return "[未提供图片]"
                return self._engine.image_to_string(img, lang=self.lang).strip()
            elif self._backend == "easyocr":
                if image_bytes:
                    img_bytes = image_bytes
                elif image_path:
                    with open(image_path, "rb") as f:
                        img_bytes = f.read()
                else:
                    return "[未提供图片]"
                result = self._engine.readtext(img_bytes)
                return "\n".join([r[1] for r in result])
        except Exception as e:
            return f"[OCR错误] {e}"
        return ""

    @property
    def is_available(self) -> bool:
        return self._backend is not None


# ============================================================
#  经验管理器
# ============================================================

class ExperienceManager:
    def __init__(self, filepath: str = "experiences_api.json"):
        self.filepath = Path(filepath)
        self.experiences: list[Experience] = []
        self._load()

    def _load(self):
        if self.filepath.exists():
            try:
                data = json.loads(self.filepath.read_text(encoding="utf-8"))
                self.experiences = [Experience(**e) for e in data]
                print(f"[经验] 已加载 {len(self.experiences)} 条经验")
            except Exception:
                self.experiences = []

    def save(self):
        data = [asdict(e) for e in self.experiences]
        self.filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, observation: str, action: str, result: str, lesson: str = ""):
        exp = Experience(
            id=len(self.experiences) + 1,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            observation=observation, action=action,
            result=result, lesson=lesson,
        )
        self.experiences.append(exp)
        self.save()

    def get_recent(self, n: int = 5) -> str:
        if not self.experiences:
            return ""
        recent = self.experiences[-n:]
        lines = []
        for e in recent:
            lines.append(
                f"#{e.id} [{e.timestamp}]\n"
                f"  观察: {e.observation[:200]}\n"
                f"  动作: {e.action[:200]}\n"
                f"  结果: {e.result[:200]}\n"
                f"  经验: {e.lesson[:200]}"
            )
        return "\n---\n".join(lines)

    def get_summary(self) -> str:
        lessons = [e.lesson for e in self.experiences if e.lesson]
        if not lessons:
            return "暂无经验总结"
        return "\n".join(f"- {l}" for l in lessons[-20:])


# ============================================================
#  游戏AI（API版）
# ============================================================

class GameAI_API:
    OUTPUT_SCHEMA = """{
    "action": "move / click / attack / use_item / wait / explore / custom",
    "target": "enemy / door / npc / item 等",
    "direction": "up / down / left / right",
    "position": "x,y",
    "confidence": "0~1",
    "reasoning": "推理过程"
}"""

    SYSTEM_PROMPT = f"""你是一个游戏AI助手。根据游戏画面（文字描述或OCR结果）做出操作决策。
必须严格以JSON格式输出动作：
{OUTPUT_SCHEMA}
规则：
1. 只输出一个JSON对象
2. 根据当前游戏状态选择最合理的动作
3. reasoning字段说明判断依据
4. confidence反映把握程度"""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1",
                 model: str = "gpt-4o", experience_file: str = "experiences_api.json"):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("请安装 openai: pip install openai")

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.ocr = LocalOCR()
        self.experience = ExperienceManager(experience_file)
        self.history: list[dict] = []
        print(f"[GameAI-API] 模型: {model}, OCR: {'可用' if self.ocr.is_available else '不可用'}")

    def get_action(self, game_state_text: str = "", image_path: str = None, image_bytes: bytes = None) -> GameAction:
        ocr_text = ""
        if image_path or image_bytes:
            ocr_text = self.ocr.recognize(image_path=image_path, image_bytes=image_bytes)

        parts = []
        if ocr_text:
            parts.append(f"[屏幕文字(OCR识别)]\n{ocr_text}")
        if game_state_text:
            parts.append(f"[游戏状态描述]\n{game_state_text}")

        exp_context = self.experience.get_recent(5)
        if exp_context:
            parts.append(f"[历史经验参考]\n{exp_context}")

        user_msg = "\n\n".join(parts) if parts else "请根据当前情况做出游戏操作决策。"

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.3, max_tokens=512,
            )
            raw = resp.choices[0].message.content.strip()
        except Exception as e:
            return GameAction(action="wait", reasoning=f"API调用失败: {e}", raw_text="")

        action = self._parse_action(raw)
        self.history.append({"observation": user_msg[:500], "action": action.to_dict()})
        return action

    def summarize_experience(self) -> str:
        if not self.history:
            return "本次会话无动作记录，无需总结。"

        history_text = json.dumps(self.history, ensure_ascii=False, indent=2)
        prompt = (
            f"以下是本次游戏会话的所有观察和动作记录：\n\n{history_text}\n\n"
            "请总结出3~5条关键经验教训，帮助未来做出更好的决策。"
            "每条经验用一句话概括，直接输出经验列表，不要多余内容。"
            "输出格式：每行一条，以 - 开头。"
        )

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是游戏策略分析专家，擅长从行动记录中提炼经验。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3, max_tokens=1024,
            )
            summary = resp.choices[0].message.content.strip()
        except Exception as e:
            summary = f"总结失败: {e}"

        for h in self.history:
            action_dict = h.get("action", {})
            self.experience.add(
                observation=h.get("observation", "")[:500],
                action=json.dumps(action_dict, ensure_ascii=False),
                result=action_dict.get("reasoning", ""),
                lesson=summary,
            )
        self.history.clear()
        return summary

    @staticmethod
    def _parse_action(raw: str) -> GameAction:
        json_str = raw
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1:
                json_str = raw[start:end + 1]
        try:
            data = json.loads(json_str)
            return GameAction(
                action=data.get("action", "wait"),
                target=data.get("target", ""),
                direction=data.get("direction", ""),
                position=data.get("position", ""),
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
                raw_text=raw,
            )
        except (json.JSONDecodeError, ValueError):
            return GameAction(action="wait", reasoning="输出解析失败", raw_text=raw)


# ============================================================
#  主程序入口
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Game AI - API版本")
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", ""), help="API Key")
    parser.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"), help="API Base URL")
    parser.add_argument("--model", default=os.environ.get("MODEL_NAME", "gpt-4o"), help="API模型名")
    args = parser.parse_args()

    print("=" * 50)
    print("  Game AI - API版本")
    print("=" * 50)

    if not args.api_key:
        print("[错误] 请通过 --api-key 或环境变量 OPENAI_API_KEY 设置API密钥")
        print("示例: python game_ai_api.py --api-key sk-xxx --base-url https://api.openai.com/v1")
        sys.exit(1)

    ai = GameAI_API(api_key=args.api_key, base_url=args.base_url, model=args.model)

    # 模拟游戏循环
    print("\n[演示] 模拟游戏回合...")
    test_scenarios = [
        "你看到前方有一个宝箱，右边有一个怪物。",
        "怪物向你冲过来了，你的血量是80%。",
        "怪物被击败，宝箱在你面前。",
    ]

    for i, scene in enumerate(test_scenarios, 1):
        print(f"\n--- 回合 {i} ---")
        print(f"场景: {scene}")
        action = ai.get_action(game_state_text=scene)
        print(f"动作: {action.action} | 目标: {action.target} | 方向: {action.direction}")
        print(f"信心: {action.confidence} | 推理: {action.reasoning}")

    print("\n--- 经验总结 ---")
    summary = ai.summarize_experience()
    print(summary)

    print("\n--- 经验库 ---")
    print(ai.experience.get_summary())


if __name__ == "__main__":
    main()
