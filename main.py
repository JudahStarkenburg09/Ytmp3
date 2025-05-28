import os
import threading
import time
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.core.window import Window
from kivy.utils import platform
from kivy.logger import Logger

# Import for Android permissions
if platform == 'android':
    try:
        from android.permissions import request_permissions, Permission
        from android.storage import primary_external_storage_path
    except ImportError:
        Logger.warning("Android: Could not import android modules")

# Mock yt-dlp for demonstration (replace with real yt-dlp in production)
class MockYTDLP:
    def __init__(self, options):
        self.options = options
    
    def download(self, urls):
        # Simulate download progress
        for i in range(101):
            time.sleep(0.05)  # Simulate download time
            if self.options.get('progress_hooks') and len(self.options['progress_hooks']) > 0:
                hook = self.options['progress_hooks'][0]
                if callable(hook):
                    hook({
                        'status': 'downloading',
                        '_percent_str': f'{i}%',
                        'downloaded_bytes': i * 10000,
                        'total_bytes': 1000000,
                        'filename': 'sample_audio.mp3'
                    })
        
        # Simulate completion
        if self.options.get('progress_hooks') and len(self.options['progress_hooks']) > 0:
            hook = self.options['progress_hooks'][0]
            if callable(hook):
                hook({
                    'status': 'finished',
                    'filename': os.path.join(self.options.get('outtmpl', ''), 'sample_audio.mp3')
                })

class ResponsiveLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = dp(20)
        self.spacing = dp(15)
        
        # Bind to window size changes for responsiveness
        Window.bind(on_resize=self.on_window_resize)
        
    def on_window_resize(self, window, width, height):
        # Adjust layout based on screen size
        if width < height:  # Portrait mode (typical for phones)
            self.padding = dp(15)
            self.spacing = dp(10)
        else:  # Landscape mode
            self.padding = dp(25)
            self.spacing = dp(20)

class YTmp3ConverterApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.is_downloading = False
        self.current_quality = 'high'
        
    def build(self):
        self.title = 'YTmp3 Converter'
        
        # Request Android permissions
        if platform == 'android':
            try:
                request_permissions([
                    Permission.WRITE_EXTERNAL_STORAGE,
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.INTERNET,
                    Permission.ACCESS_NETWORK_STATE
                ])
            except Exception as e:
                Logger.warning(f"Android: Could not request permissions: {e}")
        
        # Main layout
        main_layout = ResponsiveLayout()
        
        # Title
        title = Label(
            text='YouTube to MP3 Converter',
            font_size=sp(24),
            size_hint_y=None,
            height=dp(60),
            color=(0.2, 0.6, 1, 1),
            bold=True
        )
        main_layout.add_widget(title)
        
        # URL input section
        url_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(120),
            spacing=dp(10)
        )
        
        url_label = Label(
            text='Enter YouTube URL:',
            font_size=sp(16),
            size_hint_y=None,
            height=dp(30),
            color=(0.8, 0.8, 0.8, 1),
            text_size=(None, None),
            halign='left'
        )
        url_layout.add_widget(url_label)
        
        self.url_input = TextInput(
            multiline=False,
            font_size=sp(14),
            size_hint_y=None,
            height=dp(50),
            hint_text='https://www.youtube.com/watch?v=...',
            background_color=(0.1, 0.1, 0.1, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(1, 1, 1, 1)
        )
        url_layout.add_widget(self.url_input)
        
        main_layout.add_widget(url_layout)
        
        # Quality selection
        quality_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(50),
            spacing=dp(10)
        )
        
        quality_label = Label(
            text='Quality:',
            font_size=sp(14),
            size_hint_x=None,
            width=dp(80),
            color=(0.8, 0.8, 0.8, 1)
        )
        quality_layout.add_widget(quality_label)
        
        self.quality_btn = Button(
            text='High (320kbps)',
            font_size=sp(12),
            background_color=(0.3, 0.3, 0.3, 1),
            color=(1, 1, 1, 1)
        )
        self.quality_btn.bind(on_press=self.toggle_quality)
        quality_layout.add_widget(self.quality_btn)
        
        main_layout.add_widget(quality_layout)
        
        # Download button
        self.download_btn = Button(
            text='Download MP3',
            font_size=sp(18),
            size_hint_y=None,
            height=dp(60),
            background_color=(0.2, 0.7, 0.2, 1),
            color=(1, 1, 1, 1),
            bold=True
        )
        self.download_btn.bind(on_press=self.start_download)
        main_layout.add_widget(self.download_btn)
        
        # Progress section
        progress_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(80),
            spacing=dp(10)
        )
        
        self.progress_label = Label(
            text='Ready to download',
            font_size=sp(14),
            size_hint_y=None,
            height=dp(30),
            color=(0.8, 0.8, 0.8, 1)
        )
        progress_layout.add_widget(self.progress_label)
        
        self.progress_bar = ProgressBar(
            max=100,
            value=0,
            size_hint_y=None,
            height=dp(20)
        )
        progress_layout.add_widget(self.progress_bar)
        
        main_layout.add_widget(progress_layout)
        
        # Status/Log area
        self.status_label = Label(
            text='Status: Ready\n\nEnter a YouTube URL and tap Download MP3 to begin.',
            font_size=sp(12),
            text_size=(None, None),
            valign='top',
            color=(0.7, 0.7, 0.7, 1),
            markup=True
        )
        
        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(self.status_label)
        main_layout.add_widget(scroll)
        
        # Set initial window size for testing
        if platform != 'android':
            Window.size = (400, 700)
        
        return main_layout
    
    def toggle_quality(self, instance):
        if 'High' in instance.text:
            instance.text = 'Medium (192kbps)'
            self.current_quality = 'medium'
        elif 'Medium' in instance.text:
            instance.text = 'Low (128kbps)'
            self.current_quality = 'low'
        else:
            instance.text = 'High (320kbps)'
            self.current_quality = 'high'
    
    def show_error(self, message):
        """Show error popup"""
        content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        
        error_label = Label(
            text=message,
            text_size=(dp(300), None),
            halign='center',
            valign='middle',
            color=(1, 0.2, 0.2, 1)
        )
        content.add_widget(error_label)
        
        ok_btn = Button(
            text='OK',
            size_hint_y=None,
            height=dp(40),
            background_color=(0.2, 0.6, 1, 1)
        )
        content.add_widget(ok_btn)
        
        popup = Popup(
            title='Error',
            content=content,
            size_hint=(0.8, 0.4),
            auto_dismiss=False
        )
        
        ok_btn.bind(on_press=popup.dismiss)
        popup.open()
    
    def start_download(self, instance):
        if self.is_downloading:
            return
            
        url = self.url_input.text.strip()
        if not url:
            self.show_error('Please enter a YouTube URL')
            return
        
        if 'youtube.com' not in url.lower() and 'youtu.be' not in url.lower():
            self.show_error('Please enter a valid YouTube URL')
            return
        
        # Disable button during download
        self.is_downloading = True
        self.download_btn.disabled = True
        self.download_btn.text = 'Downloading...'
        self.download_btn.background_color = (0.5, 0.5, 0.5, 1)
        
        # Start download in separate thread
        thread = threading.Thread(target=self.download_audio, args=(url,))
        thread.daemon = True
        thread.start()
    
    def download_audio(self, url):
        try:
            # Get quality setting
            quality_map = {
                'high': '320',
                'medium': '192',
                'low': '128'
            }
            quality = quality_map.get(self.current_quality, '320')
            
            # Set download path
            if platform == 'android':
                try:
                    download_path = os.path.join(primary_external_storage_path(), 'Download', 'YTmp3')
                except:
                    download_path = '/storage/emulated/0/Download/YTmp3'
            else:
                download_path = os.path.expanduser('~/Downloads/YTmp3')
            
            # Create directory if it doesn't exist
            try:
                os.makedirs(download_path, exist_ok=True)
            except Exception as e:
                Clock.schedule_once(lambda dt: self.update_status(f'Error creating directory: {str(e)}'))
                Clock.schedule_once(lambda dt: self.reset_download_button())
                return
            
            # Configure yt-dlp options (using mock for demo)
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': quality,
                }],
                'progress_hooks': [self.progress_hook],
            }
            
            Clock.schedule_once(lambda dt: self.update_status(f'Starting download...\nURL: {url}\nQuality: {quality}kbps\nSaving to: {download_path}'))
            
            # Use mock downloader for demonstration
            # In production, replace with: import yt_dlp; ydl = yt_dlp.YoutubeDL(ydl_opts)
            ydl = MockYTDLP(ydl_opts)
            ydl.download([url])
            
        except Exception as e:
            Logger.exception("Download error")
            Clock.schedule_once(lambda dt: self.update_status(f'Error: {str(e)}'))
            Clock.schedule_once(lambda dt: self.reset_download_button())
    
    def progress_hook(self, d):
        if d['status'] == 'downloading':
            percent_str = d.get('_percent_str', '0%').replace('%', '')
            try:
                percent_val = float(percent_str)
                Clock.schedule_once(lambda dt: self.update_progress(percent_val))
                
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes', 0)
                if total > 0:
                    size_mb = total / (1024 * 1024)
                    downloaded_mb = downloaded / (1024 * 1024)
                    Clock.schedule_once(lambda dt: self.update_status(
                        f'Downloading: {percent_str}%\n'
                        f'Progress: {downloaded_mb:.1f}MB / {size_mb:.1f}MB'
                    ))
                else:
                    Clock.schedule_once(lambda dt: self.update_status(f'Downloading: {percent_str}%'))
            except ValueError:
                pass
        elif d['status'] == 'finished':
            Clock.schedule_once(lambda dt: self.update_progress(100))
            filename = os.path.basename(d.get('filename', 'audio.mp3'))
            Clock.schedule_once(lambda dt: self.update_status(
                f'✅ Download completed!\n'
                f'File: {filename}\n'
                f'Ready for next download.'
            ))
            Clock.schedule_once(lambda dt: self.reset_download_button())
    
    def update_progress(self, value):
        self.progress_bar.value = value
        self.progress_label.text = f'Progress: {value:.0f}%'
    
    def update_status(self, message):
        # Update window width for text wrapping
        self.status_label.text_size = (Window.width - dp(40), None)
        self.status_label.text = f'[color=ffffff]Status:[/color]\n{message}'
    
    def reset_download_button(self):
        self.is_downloading = False
        self.download_btn.disabled = False
        self.download_btn.text = 'Download MP3'
        self.download_btn.background_color = (0.2, 0.7, 0.2, 1)

# Entry point
if __name__ == '__main__':
    YTmp3ConverterApp().run()
