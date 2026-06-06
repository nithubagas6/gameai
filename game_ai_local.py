"""
Game AI - 本地版本
支持两种模式：
  1. API模式：使用外部API推理，本地Qwen做OCR
  2. 本地模式：完全使用本地Qwen2.5-VL-0.5B（多模态）进行推理和OCR

设备优先级：NVIDIA GPU > NPU（Intel/昇腾） > CPU
经验系统：API经验可教学本地模型，本地模型可独立总结经验，经验库共享
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
#  设备检测：GPU → NPU → CPU
# ============================================================

def detect_device():
    """自动检测最优计算设备，优先级：NVIDIA GPU > NPU > CPU"""
    device_info = {"device": "cpu", "dtype": "float32", "backend": "cpu", "name": "CPU"}

    # 1) 尝试 NVIDIA GPU (CUDA)
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_mem / (1024**3)
            device_info = {
                "device": "cuda:0",
                "dtype": "float16",
                "backend": "cuda",
                "name": f"NVIDIA {gpu_name} ({vram:.1f}GB)",
            }
            print(f"[设备] 检测到 NVIDIA GPU: {gpu_name} ({vram:.1f}GB) -> 使用 CUDA")
            return device_info
    except Exception:
        pass

    # 2) 尝试 NPU（Intel NPU via IPEX / 昇腾 NPU via torch_npu）
    # 2a) Intel NPU (通过 intel-extension-for-pytorch)
    try:
        import intel_extension_for_pytorch as ipex
        if hasattr(ipex, 'xpu') and ipex.xpu.is_available():
            device_info = {
                "device": "xpu:0",
                "dtype": "float16",
                "backend": "xpu",
                "name": f"Intel NPU/GPU ({ipex.xpu.get_device_name(0)})",
            }
            print(f"[设备] 检测到 Intel XPU: {ipex.xpu.get_device_name(0)} -> 使用 XPU")
            return device_info
    except ImportError:
        pass
    except Exception:
        pass

    # 2b) 昇腾 NPU (通过 torch_npu)
    try:
        import torch_npu
        if torch_npu.npu.is_available():
            device_info = {
                "device": "npu:0",
                "dtype": "float16",
                "backend": "npu",
                "name": "华为昇腾 NPU",
            }
            print("[设备] 检测到华为昇腾 NPU -> 使用 NPU")
            return device_info
    except ImportError:
        pass
    except Exception:
        pass

    # 3) CPU fallback
    try:
        import torch
        cpu_name = "CPU"
        if hasattr(torch, 'get_num_threads'):
            cpu_name = f"CPU ({torch.get_num_threads()} threads)"
    except ImportError:
        cpu_name = "CPU"

    device_info = {"device": "cpu", "dtype": "float32", "backend": "cpu", "name": cpu_name}
    print(f"[设备] 使用 {cpu_name}（未检测到GPU或NPU）")
    return device_info


def move_to_device(tensor_or_dict, device_info):
    """将tensor或tensor字典移动到目标设备"""
    device = device_info["device"]
    if isinstance(tensor_or_dict, dict):
        return {k: v.to(device) if hasattr(v, 'to') else v for k, v in tensor_or_dict.items()}
    elif hasattr(tensor_or_dict, 'to'):
        return tensor_or_dict.to(device)
    return tensor_or_dict


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
    source: str = ""        # api / local
    observation: str = ""
    action: str = ""
    result: str = ""
    lesson: str = ""


# ============================================================
#  经验管理器（跨模式共享）
# ============================================================

class ExperienceManager:
    """管理游戏经验，支持api/local双模式经验互通"""

    def __init__(self, filepath: str = "experiences_local.json"):
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

    def add(self, observation: str, action: str, result: str, lesson: str = "", source: str = "local"):
        exp = Experience(
            id=len(self.experiences) + 1,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            source=source,
            observation=observation,
            action=action,
            result=result,
            lesson=lesson,
        )
        self.experiences.append(exp)
        self.save()

    def get_recent(self, n: int = 5, source: str = None) -> str:
        pool = [e for e in self.experiences if source is None or e.source == source]
        if not pool:
            return ""
        recent = pool[-n:]
        lines = []
        for e in recent:
            tag = f"[{e.source.upper()}]" if e.source else ""
            lines.append(
                f"#{e.id} {tag} [{e.timestamp}]\n"
                f"  观察: {e.observation[:200]}\n"
                f"  动作: {e.action[:200]}\n"
                f"  结果: {e.result[:200]}\n"
                f"  经验: {e.lesson[:200]}"
            )
        return "\n---\n".join(lines)

    def get_lessons_for_teaching(self, max_items: int = 15) -> str:
        api_lessons = [e.lesson for e in self.experiences if e.source == "api" and e.lesson]
        if not api_lessons:
            return ""
        unique = list(dict.fromkeys(api_lessons))[-max_items:]
        return "以下是经过验证的游戏经验，请参考：\n" + "\n".join(f"- {l}" for l in unique)

    def get_summary(self) -> str:
        lessons = [e.lesson for e in self.experiences if e.lesson]
        if not lessons:
            return "暂无经验总结"
        return "\n".join(f"- {l}" for l in lessons[-20:])


# ============================================================
#  Qwen 多模态本地模型（GPU→NPU→CPU）
# ============================================================

class QwenLocalModel:
    """
    本地加载 Qwen2.5-VL-0.5B 多模态模型
    自动选择设备：NVIDIA GPU > NPU > CPU
    """

    def __init__(self, model_path: str = "Qwen/Qwen2.5-VL-0.5B-Instruct"):
        self.model_path = model_path
        self._model = None
        self._processor = None
        self._available = False
        self._device_info = None
        self._load()

    def _load(self):
        try:
            import torch
            from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor

            self._device_info = detect_device()
            device = self._device_info["device"]
            dtype_str = self._device_info["dtype"]
            dtype = torch.float16 if dtype_str == "float16" else torch.float32

            print(f"[本地模型] 正在加载 {self.model_path} 到 {self._device_info['name']} ...")

            # 使用device_map="auto"让transformers自动分配设备
            # 对于单GPU/NPU，直接指定device更可控
            if "cuda" in device:
                self._model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                    self.model_path,
                    torch_dtype=dtype,
                    device_map="auto",
                    trust_remote_code=True,
                )
            elif "npu" in device or "xpu" in device:
                self._model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                    self.model_path,
                    torch_dtype=dtype,
                    trust_remote_code=True,
                )
                self._model = self._model.to(device)
            else:
                # CPU: 使用float32以获得兼容性
                self._model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                    self.model_path,
                    torch_dtype=torch.float32,
                    trust_remote_code=True,
                )

            self._processor = AutoProcessor.from_pretrained(
                self.model_path,
                trust_remote_code=True,
            )
            self._available = True
            print(f"[本地模型] 加载成功 -> {self._device_info['name']}")
        except ImportError as e:
            print(f"[本地模型] 缺少依赖: {e}")
            print("  请运行: pip install transformers torch Pillow accelerate")
        except Exception as e:
            print(f"[本地模型] 加载失败: {e}")

    @property
    def device_info(self) -> dict:
        return self._device_info or {"device": "cpu", "name": "N/A"}

    @property
    def is_available(self) -> bool:
        return self._available

    def _get_device(self):
        """获取模型所在设备"""
        if self._model is not None:
            try:
                return next(self._model.parameters()).device
            except StopIteration:
                pass
        return self._device_info.get("device", "cpu") if self._device_info else "cpu"

    def generate_text(self, prompt: str, max_new_tokens: int = 512) -> str:
        if not self._available:
            return "[模型不可用]"
        try:
            import torch
            messages = [
                {"role": "system", "content": "你是游戏AI助手，根据游戏状态做出决策。"},
                {"role": "user", "content": prompt},
            ]
            text = self._processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = self._processor(text=[text], return_tensors="pt", padding=True)
            inputs = inputs.to(self._get_device())

            with torch.no_grad():
                output = self._model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    do_sample=True,
                    temperature=0.3,
                    top_p=0.9,
                )
            generated = output[0][inputs["input_ids"].shape[1]:]
            return self._processor.decode(generated, skip_special_tokens=True).strip()
        except Exception as e:
            return f"[生成错误] {e}"

    def ocr_from_image(self, image_path: str = None, image_bytes: bytes = None) -> str:
        if not self._available:
            return "[模型不可用]"
        try:
            import torch
            from PIL import Image
            import io

            if image_bytes:
                image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            elif image_path:
                image = Image.open(image_path).convert("RGB")
            else:
                return "[未提供图片]"

            messages = [{
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": "请识别这张游戏截图中的所有文字内容，只输出文字，不要解释。"},
                ],
            }]
            text = self._processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = self._processor(text=[text], images=[image], return_tensors="pt", padding=True)
            inputs = inputs.to(self._get_device())

            with torch.no_grad():
                output = self._model.generate(**inputs, max_new_tokens=256, do_sample=False)
            generated = output[0][inputs["input_ids"].shape[1]:]
            return self._processor.decode(generated, skip_special_tokens=True).strip()
        except Exception as e:
            return f"[OCR错误] {e}"

    def generate_with_image(self, prompt: str, image_path: str = None, image_bytes: bytes = None, max_new_tokens: int = 512) -> str:
        if not self._available:
            return "[模型不可用]"
        try:
            import torch
            from PIL import Image
            import io

            if image_bytes:
                image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            elif image_path:
                image = Image.open(image_path).convert("RGB")
            else:
                return self.generate_text(prompt, max_new_tokens)

            messages = [{
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt},
                ],
            }]
            text = self._processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = self._processor(text=[text], images=[image], return_tensors="pt", padding=True)
            inputs = inputs.to(self._get_device())

            with torch.no_grad():
                output = self._model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    do_sample=True,
                    temperature=0.3,
                    top_p=0.9,
                )
            generated = output[0][inputs["input_ids"].shape[1]:]
            return self._processor.decode(generated, skip_special_tokens=True).strip()
        except Exception as e:
            return f"[多模态生成错误] {e}"


# ============================================================
#  游戏AI（本地版）
# ============================================================

class GameAI_Local:
    """本地版游戏AI，支持api/local双模式，经验教学与共享"""

    OUTPUT_SCHEMA = """{
    "action": "move / click / attack / use_item / wait / explore / custom",
    "target": "enemy / door / npc / item 等",
    "direction": "up / down / left / right",
    "position": "x,y",
    "confidence": "0~1",
    "reasoning": "推理过程"
}"""

    SYSTEM_PROMPT = f"""你是一个游戏AI助手。根据游戏状态做出操作决策。
必须严格以JSON格式输出动作：
{OUTPUT_SCHEMA}
规则：
1. 只输出一个JSON对象
2. 选择最合理的动作
3. reasoning字段说明判断依据
4. confidence反映把握程度"""

    def __init__(
        self,
        mode: str = "local",
        api_key: str = "",
        base_url: str = "https://gvmz.systems/v1",
        api_model: str = "gpt-5.4-mini",
        model_path: str = "Qwen/Qwen2.5-VL-0.5B-Instruct",
        experience_file: str = "experiences_local.json",
    ):
        self.mode = mode
        self.experience = ExperienceManager(experience_file)
        self.history: list[dict] = []

        # 始终加载本地模型
        self.local_model = QwenLocalModel(model_path)

        # API配置
        self._api_key = api_key
        self._api_base_url = base_url.rstrip("/")
        self._api_model = api_model

        print(f"[GameAI-Local] 模式: {mode} | 本地模型: {'可用' if self.local_model.is_available else '不可用'}")

    def switch_mode(self, mode: str):
        if mode not in ("api", "local"):
            raise ValueError("mode 必须是 'api' 或 'local'")
        self.mode = mode
        print(f"[GameAI-Local] 已切换到 {mode} 模式")

    def get_action(self, game_state_text: str = "", image_path: str = None, image_bytes: bytes = None) -> GameAction:
        # OCR（始终用本地多模态模型）
        ocr_text = ""
        if image_path or image_bytes:
            ocr_text = self.local_model.ocr_from_image(image_path=image_path, image_bytes=image_bytes)

        user_msg = self._build_prompt(game_state_text, ocr_text)

        if self.mode == "api":
            raw = self._call_api(user_msg, image_path, image_bytes)
        else:
            raw = self._call_local(user_msg, image_path, image_bytes)

        action = self._parse_action(raw)

        self.history.append({
            "observation": user_msg[:500],
            "action": action.to_dict(),
        })
        return action

    def summarize_experience(self) -> str:
        if not self.history:
            return "本次会话无动作记录。"

        history_text = json.dumps(self.history, ensure_ascii=False, indent=2)
        prompt = (
            f"以下是本次游戏会话的观察和动作记录：\n\n{history_text}\n\n"
            "请总结3~5条关键经验，帮助未来做出更好的决策。\n每条经验用一句话概括，以 - 开头。"
        )

        if self.mode == "api":
            summary = self._call_api(prompt)
        else:
            summary = self._call_local(prompt)

        for h in self.history:
            action_dict = h.get("action", {})
            self.experience.add(
                observation=h.get("observation", "")[:500],
                action=json.dumps(action_dict, ensure_ascii=False),
                result=action_dict.get("reasoning", ""),
                lesson=summary,
                source=self.mode,
            )
        self.history.clear()
        return summary

    def teach_local_model(self) -> str:
        api_lessons = self.experience.get_lessons_for_teaching()
        if not api_lessons:
            return "没有API模式的经验可以教学。"

        teach_prompt = (
            f"{api_lessons}\n\n请将以上经验内化为你自己的游戏策略知识，用简洁的规则形式重新表述，每条以 - 开头。"
        )

        if self.local_model.is_available:
            result = self.local_model.generate_text(teach_prompt, max_new_tokens=512)
            self.experience.add(
                observation="[教学] API经验→本地模型",
                action="teach", result="",
                lesson=result, source="local",
            )
            return result
        return "本地模型不可用，无法教学。"

    def _build_prompt(self, game_state_text: str, ocr_text: str) -> str:
        parts = []
        if self.mode == "local":
            teaching = self.experience.get_lessons_for_teaching(max_items=5)
            if teaching:
                parts.append(f"[经验指导]\n{teaching}")
        recent = self.experience.get_recent(3)
        if recent:
            parts.append(f"[近期经验]\n{recent}")
        if ocr_text:
            parts.append(f"[屏幕文字]\n{ocr_text}")
        if game_state_text:
            parts.append(f"[游戏状态]\n{game_state_text}")
        return "\n\n".join(parts) if parts else "请根据当前情况做出游戏操作决策。"

    def _call_api(self, prompt: str, image_path: str = None, image_bytes: bytes = None) -> str:
        if not self._api_key:
            return '{"action":"wait","reasoning":"API密钥未设置，请设置api-key"}'

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        if image_path or image_bytes:
            try:
                if image_bytes:
                    b64 = base64.b64encode(image_bytes).decode()
                elif image_path:
                    with open(image_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode()
                else:
                    b64 = ""
                if b64:
                    messages[1]["content"] = [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    ]
            except Exception:
                pass

        for attempt in range(3):
            try:
                import requests as req
                resp = req.post(
                    f"{self._api_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self._api_model,
                        "messages": messages,
                        "temperature": 0.3,
                        "max_tokens": 512,
                        "stream": True,
                    },
                    timeout=180,
                    stream=True,
                )
                resp.raise_for_status()
                result = ""
                for line in resp.iter_lines():
                    if not line:
                        continue
                    decoded = line.decode("utf-8")
                    if not decoded.startswith("data: ") or decoded == "data: [DONE]":
                        continue
                    try:
                        chunk = json.loads(decoded[6:])
                        delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        result += delta
                    except (json.JSONDecodeError, IndexError, KeyError):
                        pass
                if result.strip():
                    return result.strip()
            except Exception as e:
                if attempt < 2:
                    print(f"  [重试] 第{attempt+1}次失败: {e}, 等待3秒后重试...")
                    time.sleep(3)
                else:
                    return f'{{"action":"wait","reasoning":"API调用失败: {e}"}}'

    def _call_local(self, prompt: str, image_path: str = None, image_bytes: bytes = None) -> str:
        if not self.local_model.is_available:
            return '{"action":"wait","reasoning":"本地模型不可用"}'

        full_prompt = f"{self.SYSTEM_PROMPT}\n\n{prompt}\n\n请严格输出JSON格式的动作。"

        if image_path or image_bytes:
            return self.local_model.generate_with_image(full_prompt, image_path=image_path, image_bytes=image_bytes)
        return self.local_model.generate_text(full_prompt)

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

    parser = argparse.ArgumentParser(description="Game AI - 本地版")
    parser.add_argument("--mode", choices=["api", "local"], default="local", help="运行模式")
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", ""), help="API Key")
    parser.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL", "https://gvmz.systems/v1"), help="API Base URL")
    parser.add_argument("--api-model", default=os.environ.get("MODEL_NAME", "gpt-5.4-mini"), help="API模型名")
    parser.add_argument("--model-path", default="Qwen/Qwen2.5-VL-0.5B-Instruct", help="本地模型路径")
    parser.add_argument("--teach", action="store_true", help="执行API经验教学")
    args = parser.parse_args()

    print("=" * 50)
    print("  Game AI - 本地版")
    print(f"  模式: {args.mode}")
    print("=" * 50)

    ai = GameAI_Local(
        mode=args.mode,
        api_key=args.api_key,
        base_url=args.base_url,
        api_model=args.api_model,
        model_path=args.model_path,
    )

    if args.teach:
        print("\n[教学] 正在将API经验传授给本地模型...")
        result = ai.teach_local_model()
        print(f"教学结果:\n{result}")
        return

    # 模拟游戏循环
    print("\n[演示] 模拟游戏回合...")
    test_scenarios = [
        "你看到前方有一个宝箱，右边有一个怪物。",
        "怪物向你冲过来了，你的血量是80%。",
        "怪物被击败，宝箱在你面前。",
    ]

    for i, scene in enumerate(test_scenarios, 1):
        if i > 1 and args.mode == "api":
            time.sleep(2)  # API模式请求间隔，避免限流
        print(f"\n--- 回合 {i} ---")
        print(f"场景: {scene}")
        action = ai.get_action(game_state_text=scene)
        print(f"动作: {action.action} | 目标: {action.target} | 方向: {action.direction}")
        print(f"信心: {action.confidence} | 推理: {action.reasoning}")

    print("\n--- 经验总结 ---")
    summary = ai.summarize_experience()
    print(summary)

    if args.mode == "local" and ai.experience.get_lessons_for_teaching():
        print("\n--- API经验教学给本地模型 ---")
        teach_result = ai.teach_local_model()
        print(teach_result)

    print("\n--- 经验库 ---")
    print(ai.experience.get_summary())


if __name__ == "__main__":
    main()
