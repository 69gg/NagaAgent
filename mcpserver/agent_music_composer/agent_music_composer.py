import json
import os
import numpy as np
from agents import Agent
import asyncio
from typing import List, Dict, Any, Optional, Tuple
import tempfile
from pathlib import Path

try:
    from pydub import AudioSegment
    from pydub.generators import Sine
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

class MusicComposerAgent(Agent):
    name = "MusicComposerAgent"
    instructions = "音乐编排MCP Agent，支持根据频率列表和时长列表生成音乐曲谱。建议一次调用完成所有音符转换和音乐生成，避免多轮调用导致的播放混乱。"
    
    def __init__(self):
        super().__init__(
            name=self.name,
            instructions=self.instructions,
            tools=[],
            model="music-composer"
        )
        
        # 音符频率映射 (A4 = 440Hz)
        self.note_frequencies = {
            'C': 261.63,
            'C#': 277.18,
            'D': 293.66,
            'D#': 311.13,
            'E': 329.63,
            'F': 349.23,
            'F#': 369.99,
            'G': 392.00,
            'G#': 415.30,
            'A': 440.00,
            'A#': 466.16,
            'B': 493.88
        }
        
        # 和弦音程映射
        self.chord_intervals = {
            'major': [0, 4, 7],          # 大三和弦
            'minor': [0, 3, 7],          # 小三和弦
            'diminished': [0, 3, 6],     # 减三和弦
            'augmented': [0, 4, 8],       # 增三和弦
            'major7': [0, 4, 7, 11],     # 大七和弦
            'minor7': [0, 3, 7, 10]      # 小七和弦
        }
        
        # 创建输出目录
        self.output_dir = Path("logs/audio_temp")
        self.output_dir.mkdir(exist_ok=True)
        
        # 播放队列管理
        self.play_queue = []
        self.is_playing = False
        self.play_lock = asyncio.Lock()
        
    def note_to_frequency(self, note: str, octave: int = 4) -> float:
        """将音符转换为频率"""
        if note not in self.note_frequencies:
            raise ValueError(f"不支持的音符: {note}")
        
        # 确保octave是整数类型
        if isinstance(octave, str):
            try:
                octave = int(octave)
            except ValueError:
                raise ValueError(f"无效的八度值: {octave}")
        
        base_freq = self.note_frequencies[note]
        # 根据八度调整频率
        return base_freq * (2 ** (octave - 4))
    
    def generate_chord_frequencies(self, chord_type: str, root_note: str = 'C', octave: int = 4) -> List[float]:
        """生成和弦频率列表"""
        if chord_type not in self.chord_intervals:
            raise ValueError(f"不支持的和弦类型: {chord_type}")
        
        if root_note not in self.note_frequencies:
            raise ValueError(f"不支持的根音: {root_note}")
        
        root_freq = self.note_to_frequency(root_note, octave)
        intervals = self.chord_intervals[chord_type]
        
        # 计算和弦中各音的频率
        chord_freqs = []
        for interval in intervals:
            if interval <= 12:  # 同一个八度内
                freq = root_freq * (2 ** (interval / 12))
            else:  # 跨八度
                freq = root_freq * (2 ** ((interval % 12) / 12)) * (2 ** (interval // 12))
            chord_freqs.append(freq)
        
        return chord_freqs
    
    def generate_sine_wave(self, frequency: float, duration: float, sample_rate: int = 44100) -> np.ndarray:
        """生成正弦波音频数据"""
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave = np.sin(2 * np.pi * frequency * t)
        
        # 添加淡入淡出效果
        fade_samples = int(sample_rate * 0.01)  # 10ms淡入淡出
        fade_in = np.linspace(0, 1, fade_samples)
        fade_out = np.linspace(1, 0, fade_samples)
        
        if len(wave) > 2 * fade_samples:
            wave[:fade_samples] *= fade_in
            wave[-fade_samples:] *= fade_out
        
        return wave
    
    def compose_music(self, frequencies: List[float], durations: List[float], 
                     output_format: str = 'wav', sample_rate: int = 44100) -> str:
        """根据频率列表和时长列表生成音乐"""
        if not PYDUB_AVAILABLE:
            raise RuntimeError("pydub库未安装，无法生成音频文件")
        
        if len(frequencies) != len(durations):
            raise ValueError("频率列表和时长列表长度必须相同")
        
        if not frequencies:
            raise ValueError("频率列表不能为空")
        
        # 生成音频段
        combined_audio = AudioSegment.empty()
        
        for freq, duration in zip(frequencies, durations):
            if freq <= 0 or duration <= 0:
                continue
            
            # 生成正弦波
            sine_wave = Sine(freq)
            note_audio = sine_wave.to_audio_segment(duration=duration * 1000)  # 转换为毫秒
            
            # 添加淡入淡出效果
            note_audio = note_audio.fade_in(10).fade_out(10)
            
            combined_audio += note_audio
        
        # 生成输出文件路径
        timestamp = int(asyncio.get_event_loop().time())
        output_filename = f"music_composition_{timestamp}.{output_format}"
        output_path = self.output_dir / output_filename
        
        # 导出音频文件
        combined_audio.export(
            output_path,
            format=output_format,
            parameters=["-ar", str(sample_rate)]
        )
        
        return str(output_path)
    
    def compose_music_numpy(self, frequencies: List[float], durations: List[float], 
                           output_format: str = 'wav', sample_rate: int = 44100) -> str:
        """使用numpy生成音乐（备用方案）"""
        if len(frequencies) != len(durations):
            raise ValueError("频率列表和时长列表长度必须相同")
        
        if not frequencies:
            raise ValueError("频率列表不能为空")
        
        # 生成音频数据
        combined_wave = np.array([])
        
        for freq, duration in zip(frequencies, durations):
            if freq <= 0 or duration <= 0:
                continue
            
            wave = self.generate_sine_wave(freq, duration, sample_rate)
            combined_wave = np.concatenate([combined_wave, wave])
        
        # 归一化
        if len(combined_wave) > 0:
            combined_wave = np.int16(combined_wave / np.max(np.abs(combined_wave)) * 32767)
        
        # 生成输出文件路径
        timestamp = int(asyncio.get_event_loop().time())
        output_filename = f"music_composition_{timestamp}.{output_format}"
        output_path = self.output_dir / output_filename
        
        # 保存为WAV文件
        try:
            import scipy.io.wavfile
            scipy.io.wavfile.write(output_path, sample_rate, combined_wave)
            return str(output_path)
        except ImportError:
            # 如果没有scipy，保存为原始数据
            with open(output_path, 'wb') as f:
                f.write(combined_wave.tobytes())
            return str(output_path)
    
    async def handle_handoff(self, data: dict) -> str:
        """处理handoff请求"""
        tool_name = data.get("tool_name")
        
        try:
            if tool_name == "生成曲谱":
                return await self._handle_compose_music(data)
            elif tool_name == "音符转换":
                return await self._handle_note_conversion(data)
            elif tool_name == "生成和弦":
                return await self._handle_chord_generation(data)
            elif tool_name == "播放音乐":
                return await self._handle_play_music(data)
            else:
                return json.dumps({
                    "status": "error",
                    "message": f"未知操作: {tool_name}",
                    "data": ""
                }, ensure_ascii=False)
        
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"执行失败: {str(e)}",
                "data": ""
            }, ensure_ascii=False)
    
    async def _handle_compose_music(self, data: dict) -> str:
        """处理生成曲谱请求"""
        frequencies = data.get("frequencies", [])
        durations = data.get("durations", [])
        
        # 处理字符串格式的参数
        if isinstance(frequencies, str):
            frequencies = [float(x.strip()) for x in frequencies.strip('[]').split(',')]
        
        if isinstance(durations, str):
            durations = [float(x.strip()) for x in durations.strip('[]').split(',')]
        
        # 如果没有提供durations，默认每个音符0.5秒
        if not durations and frequencies:
            durations = [0.5] * len(frequencies)
        
        # 生成音乐并播放
        try:
            if PYDUB_AVAILABLE:
                file_path = self.compose_music(frequencies, durations, "wav", 44100)
            else:
                file_path = self.compose_music_numpy(frequencies, durations, "wav", 44100)
            
            # 自动播放生成的音乐
            await self._play_with_python(file_path, True)
            
            return json.dumps({
                "status": "ok",
                "message": f"音乐生成并播放成功，包含{len(frequencies)}个音符，总时长{sum(durations):.2f}秒",
                "data": f"已生成包含{len(frequencies)}个音符的音乐，总时长{sum(durations):.2f}秒"
            }, ensure_ascii=False)
        
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"音乐生成失败: {str(e)}",
                "data": ""
            }, ensure_ascii=False)
    
    async def _handle_note_conversion(self, data: dict) -> str:
        """处理音符转换请求"""
        notes = data.get("notes", [])
        octave = data.get("octave", 4)
        
        # 处理字符串格式的notes参数
        if isinstance(notes, str):
            notes_str = notes.strip('[]\'"')
            notes = [note.strip().strip('\'"') for note in notes_str.split(',') if note.strip()]
        
        # 转换音符为频率
        frequencies = []
        for note in notes:
            try:
                freq = self.note_to_frequency(note, octave)
                frequencies.append(freq)
            except ValueError:
                continue
        
        # 自动生成音乐并播放
        try:
            if frequencies:
                # 默认每个音符0.5秒
                durations = [0.5] * len(frequencies)
                
                if PYDUB_AVAILABLE:
                    file_path = self.compose_music(frequencies, durations, "wav", 44100)
                else:
                    file_path = self.compose_music_numpy(frequencies, durations, "wav", 44100)
                
                # 自动播放生成的音乐
                await self._play_with_python(file_path, True)
                
                return json.dumps({
                    "status": "ok",
                    "message": f"成功转换{len(frequencies)}个音符为频率并自动播放，总时长{sum(durations):.2f}秒",
                    "data": f"已生成包含{len(frequencies)}个音符的音乐，总时长{sum(durations):.2f}秒"
                }, ensure_ascii=False)
            else:
                return json.dumps({
                    "status": "error",
                    "message": "没有有效的音符可转换",
                    "data": ""
                }, ensure_ascii=False)
        
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"音符转换和播放失败: {str(e)}",
                "data": ""
            }, ensure_ascii=False)
    
    async def _handle_chord_generation(self, data: dict) -> str:
        """处理生成和弦请求"""
        chord_type = data.get("chord_type", "major")
        root_note = data.get("root_note", "C")
        octave = data.get("octave", 4)
        duration = data.get("duration", 1.0)
        
        # 生成和弦频率
        try:
            frequencies = self.generate_chord_frequencies(chord_type, root_note, octave)
            
            # 生成和弦音频
            if PYDUB_AVAILABLE:
                file_path = self.compose_music(frequencies, [duration] * len(frequencies), "wav", 44100)
            else:
                file_path = self.compose_music_numpy(frequencies, [duration] * len(frequencies), "wav", 44100)
            
            # 自动播放生成的和弦
            await self._play_with_python(file_path, True)
            
            return json.dumps({
                "status": "ok",
                "message": f"成功生成并播放{root_note}{chord_type}和弦，时长{duration}秒",
                "data": f"已生成{root_note}{chord_type}和弦，时长{duration}秒"
            }, ensure_ascii=False)
        
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"和弦生成失败: {str(e)}",
                "data": ""
            }, ensure_ascii=False)
    
    async def _handle_play_music(self, data: dict) -> str:
        """处理播放音乐请求"""
        file_path = data.get("file_path", "")
        play_method = data.get("play_method", "python")  # 默认使用python播放
        auto_close = data.get("auto_close", True)  # 默认自动关闭
        
        # 验证参数
        if not file_path:
            return json.dumps({
                "status": "error",
                "message": "缺少file_path参数",
                "data": ""
            }, ensure_ascii=False)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return json.dumps({
                "status": "error",
                "message": f"文件不存在: {file_path}",
                "data": ""
            }, ensure_ascii=False)
        
        try:
            if play_method == "system":
                # 使用系统默认播放器播放音乐
                return await self._play_with_system(file_path, auto_close)
            else:
                # 使用Python方法播放（默认）
                return await self._play_with_python(file_path, auto_close)
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"播放失败: {str(e)}",
                "data": ""
            }, ensure_ascii=False)
    
    async def _play_with_system(self, file_path: str, auto_close: bool = False) -> str:
        """使用系统播放器播放音乐"""
        import platform
        import subprocess
        import threading
        import time
        
        system = platform.system()
        
        def play_and_close():
            try:
                if system == "Windows":
                    # Windows系统使用start命令
                    process = subprocess.Popen(["start", "", "/wait", file_path], shell=True)
                elif system == "Darwin":  # macOS
                    # macOS使用open命令
                    process = subprocess.Popen(["open", "-W", file_path])
                elif system == "Linux":
                    # Linux系统使用xdg-open命令
                    process = subprocess.Popen(["xdg-open", file_path])
                else:
                    return
                
                # 如果设置了自动关闭，等待播放完成后关闭
                if auto_close and system == "Windows":
                    process.wait()
                    # 在Windows上，播放完成后关闭媒体播放器
                    subprocess.run(["taskkill", "/f", "/im", "wmplayer.exe"], shell=True)
                    subprocess.run(["taskkill", "/f", "/im", "vlc.exe"], shell=True)
                    
            except Exception as e:
                print(f"播放或关闭时出错: {e}")
        
        if auto_close:
            # 在后台线程中播放并自动关闭
            thread = threading.Thread(target=play_and_close, daemon=True)
            thread.start()
            
            return json.dumps({
                "status": "ok",
                "message": f"开始播放音乐文件（自动关闭）: {file_path}",
                "data": {
                    "file_path": file_path,
                    "system": system,
                    "play_method": "system",
                    "auto_close": True
                }
            }, ensure_ascii=False)
        else:
            # 立即播放
            if system == "Windows":
                subprocess.run(["start", "", file_path], shell=True, check=True)
            elif system == "Darwin":
                subprocess.run(["open", file_path], check=True)
            elif system == "Linux":
                subprocess.run(["xdg-open", file_path], check=True)
            
            return json.dumps({
                "status": "ok",
                "message": f"开始播放音乐文件: {file_path}",
                "data": {
                    "file_path": file_path,
                    "system": system,
                    "play_method": "system",
                    "auto_close": False
                }
            }, ensure_ascii=False)
    
    async def _play_with_python(self, file_path: str, auto_close: bool = False) -> str:
        """使用Python库播放音乐（支持队列管理）"""
        async with self.play_lock:
            # 如果正在播放，添加到队列
            if self.is_playing:
                self.play_queue.append(file_path)
                
                return json.dumps({
                    "status": "ok",
                    "message": f"音乐已添加到播放队列，当前队列长度: {len(self.play_queue)}",
                    "data": {
                        "file_path": file_path,
                        "queue_position": len(self.play_queue),
                        "play_method": "python",
                        "auto_close": auto_close
                    }
                }, ensure_ascii=False)
            else:
                # 直接播放
                return await self._play_audio_file(file_path, auto_close)
    
    async def _play_audio_file(self, file_path: str, auto_close: bool) -> str:
        """实际播放音频文件"""
        try:
            self.is_playing = True
            
            # 尝试使用不同的Python音频库
            audio_libraries = [
                self._play_with_simpleaudio,
                self._play_with_winsound,
                self._play_with_pyaudio,
                self._play_with_sounddevice
            ]
            
            for play_func in audio_libraries:
                try:
                    result = await play_func(file_path, auto_close)
                    if result:
                        # 播放完成后处理下一个
                        await self._process_next_in_queue()
                        return result
                except Exception as e:
                    continue
            
            # 如果所有播放方法都失败，处理下一个
            await self._process_next_in_queue()
            
            return json.dumps({
                "status": "error",
                "message": "无法找到可用的Python音频库",
                "data": ""
            }, ensure_ascii=False)
            
        except Exception as e:
            await self._process_next_in_queue()
            
            return json.dumps({
                "status": "error",
                "message": f"Python播放失败: {str(e)}",
                "data": ""
            }, ensure_ascii=False)
    
    async def _process_next_in_queue(self):
        """处理队列中的下一个文件"""
        self.is_playing = False
        
        if self.play_queue:
            next_file = self.play_queue.pop(0)
            # 在后台任务中播放下一个文件
            asyncio.create_task(self._play_audio_file(next_file, True))
    
    async def _play_with_pyaudio(self, file_path: str, auto_close: bool) -> str:
        """使用PyAudio播放音乐"""
        try:
            import pyaudio
            import wave
            import threading
            
            def play_audio():
                try:
                    # 打开WAV文件
                    wf = wave.open(file_path, 'rb')
                    
                    # 初始化PyAudio
                    p = pyaudio.PyAudio()
                    
                    # 打开音频流
                    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                                  channels=wf.getnchannels(),
                                  rate=wf.getframerate(),
                                  output=True)
                    
                    # 读取数据并播放
                    data = wf.readframes(1024)
                    while len(data) > 0:
                        stream.write(data)
                        data = wf.readframes(1024)
                    
                    # 停止和关闭流
                    stream.stop_stream()
                    stream.close()
                    p.terminate()
                    wf.close()
                    
                except Exception as e:
                    print(f"PyAudio播放错误: {e}")
            
            # 在后台线程中播放
            thread = threading.Thread(target=play_audio, daemon=True)
            thread.start()
            
            return json.dumps({
                "status": "ok",
                "message": f"使用PyAudio开始播放音乐文件: {file_path}",
                "data": {
                    "file_path": file_path,
                    "play_method": "python",
                    "library": "pyaudio",
                    "auto_close": auto_close
                }
            }, ensure_ascii=False)
            
        except ImportError:
            return None
    
    async def _play_with_simpleaudio(self, file_path: str, auto_close: bool) -> str:
        """使用simpleaudio播放音乐"""
        try:
            import simpleaudio as sa
            import threading
            
            def play_audio():
                try:
                    # 播放WAV文件
                    wave_obj = sa.WaveObject.from_wave_file(file_path)
                    play_obj = wave_obj.play()
                    play_obj.wait_done()
                except Exception as e:
                    print(f"simpleaudio播放错误: {e}")
            
            # 在后台线程中播放
            thread = threading.Thread(target=play_audio, daemon=True)
            thread.start()
            
            return json.dumps({
                "status": "ok",
                "message": f"使用simpleaudio开始播放音乐文件: {file_path}",
                "data": {
                    "file_path": file_path,
                    "play_method": "python",
                    "library": "simpleaudio",
                    "auto_close": auto_close
                }
            }, ensure_ascii=False)
            
        except ImportError:
            return None
    
    async def _play_with_sounddevice(self, file_path: str, auto_close: bool) -> str:
        """使用sounddevice播放音乐"""
        try:
            import sounddevice as sd
            import soundfile as sf
            import threading
            
            def play_audio():
                try:
                    # 读取音频文件
                    data, samplerate = sf.read(file_path)
                    # 播放音频
                    sd.play(data, samplerate)
                    sd.wait()
                except Exception as e:
                    print(f"sounddevice播放错误: {e}")
            
            # 在后台线程中播放
            thread = threading.Thread(target=play_audio, daemon=True)
            thread.start()
            
            return json.dumps({
                "status": "ok",
                "message": f"使用sounddevice开始播放音乐文件: {file_path}",
                "data": {
                    "file_path": file_path,
                    "play_method": "python",
                    "library": "sounddevice",
                    "auto_close": auto_close
                }
            }, ensure_ascii=False)
            
        except ImportError:
            return None
    
    async def _play_with_winsound(self, file_path: str, auto_close: bool) -> str:
        """使用winsound播放音乐（仅Windows，仅支持WAV）"""
        try:
            import winsound
            import threading
            
            def play_audio():
                try:
                    # 播放WAV文件
                    winsound.PlaySound(file_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                except Exception as e:
                    print(f"winsound播放错误: {e}")
            
            # 在后台线程中播放
            thread = threading.Thread(target=play_audio, daemon=True)
            thread.start()
            
            return json.dumps({
                "status": "ok",
                "message": f"使用winsound开始播放音乐文件: {file_path}",
                "data": {
                    "file_path": file_path,
                    "play_method": "python",
                    "library": "winsound",
                    "auto_close": auto_close
                }
            }, ensure_ascii=False)
            
        except ImportError:
            return None

def create_music_composer_agent():
    """创建音乐编排Agent实例"""
    return MusicComposerAgent()