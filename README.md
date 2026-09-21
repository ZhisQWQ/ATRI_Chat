# ATRI_Chat  

## 项目说明  

<img src="https://github.com/Therqwq/ATRI_Chat/blob/main/Show/Image[1].png" alt="image">  

- 本项目是是一个AI对话系统，实现了TTS、翻译、AI对话的完整流程，同时正在逐步完善记忆系统  
- 语音合成部分使用了GPT-SoVITS工具，其他所有组件均由本项目独立开发  
- 项目素材取自网络、AI生成等，代码编写由Vide Coding完成  

**使用说明和素材请移步至**：`https://www.bilibili.com/video/BV1pRhezaEjW/?spm_id_from=333.1387.homepage.video_card.click`  

## 版权与法律声明  

### GPT-SoVITS使用声明  

- 本项目语音合成模块使用了GPT-SoVITS 开源项目
- MIT许可证不要求衍生作品必须开源，允许将其用于专有代码库  
- 本项目已包含GPT-SoVITS的原始版权声明和许可证文件   

### 原始素材版权声明  

- 本项目训练所用的所有原始音频素材均由开发者自行收集整理，仅供学习和交流使用，如有侵权，请联系删除  
- 重要提示：根据GPT-SoVITS项目声明，使用本项目生成的语音内容，您必须确保拥有原始素材的合法授权，否则可能构成侵权  
- 任何使用本项目生成的内容，使用者需自行承担法律责任，本项目不对素材版权问题负责  

### 项目代码版权声明  

- 本项目除GPT-SoVITS相关组件外的所有代码采用MIT许可证发布  
- MIT许可证唯一要求是包含原始版权声明和许可证  
- 与GPL等copyleft许可证不同，MIT许可证不要求衍生作品采用相同的许可证  

### 免责声明  

**素材责任**：本项目不提供任何音频素材，使用者必须自行获取合法授权的训练数据。使用未经授权的音频素材训练模型可能导致法律纠纷  
生成内容责任：使用本项目生成的任何语音内容，其法律责任由使用者自行承担。GPT-SoVITS项目明确表示生成物不属于该工具，其合法性取决于原始素材的授权情况  
**API使用**：本项目集成了第三方API（如DeepSeek API），使用者需遵守这些API的服务条款，本项目不对API使用产生的问题负责  
无担保声明：本软件按"原样"提供，不提供任何形式的明示或暗示担保，包括但不限于适销性、特定用途适用性和非侵权性的担保  
 
### 使用建议  

**严格遵守素材版权**：在使用本项目前，请确保您拥有训练数据的合法使用权，或已获得原音频素材所有者的明确授权  
**明确标注来源**：如果您基于本项目进行二次开发，请保留GPT-SoVITS的版权声明，并明确区分哪些部分属于原项目，哪些是您的贡献  
**商业用途注意**：虽然MIT许可证允许商业使用 ，但您必须确保训练数据的商业使用权限，否则可能面临法律风险  

### 致谢  

- 感谢GPT-SoVITS项目提供的开源语音合成工具  
- 感谢所有为开源社区做出贡献的开发者  

## 使用说明  

### Linux  

1. 打包下载源码文件，并解压
2. 打开终端进入当前目录，并创建 python 虚拟环境
```
python -m venv venv
```
3. 激活虚拟环节，如果你的命令解释器是fish的话
```
source venv/bin/activate.fish
```
4. 安装依赖软件包
```
pip install requests pygame-ce volcengine-python-sdk openai zai-sdk PyQt6 volcengine pillow cryptography pyyaml
```
5. 等待安装完成后，先运行设置以配置API：`python ./ATRI_Chat_Setting.py`，根据引导配置好聊天API和翻译API并设置好超级密码
- 超级密码用于恢复配置，遗失超级密码你的密钥数据将丢失  
6. 配置完成后，直接运行即可：`python ./ATRI_Chat.py`
> 语音功能需要部署 GPT-Sovits，可以自行部署 Docker 即可 

### Windows  

- 与 Linux 步骤相同  
