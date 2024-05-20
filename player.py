import configparser, subprocess, pkg_resources,  sys, os, logging, threading, time, random

def check_and_install_package(package_name, apt_name=None):
    try:
        pkg_resources.get_distribution(package_name)
        return True
    except pkg_resources.DistributionNotFound:
        pass
    apt_installed = False
    if apt_name:
        apt_check = subprocess.run(['dpkg', '-s', apt_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        apt_installed = apt_check.returncode == 0 and "Status: install ok installed" in apt_check.stdout.decode()
    pip_installed = False
    pip_check = subprocess.run(['pip3', 'show', package_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    pip_installed = pip_check.returncode == 0
    if apt_installed or pip_installed:
        return True
    if package_name == 'vlc':
        vlc_check = subprocess.run(['which', 'vlc'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        vlc_installed = vlc_check.returncode == 0
        if vlc_installed:
            return True
        else:
            try:
                subprocess.check_call(['sudo', 'apt', 'install', '-y', 'mpv'])
                return True
            except subprocess.CalledProcessError:
                pass
    if apt_name:
        try:
            subprocess.check_call(['sudo', 'apt', 'install', '-y', apt_name])
            return True
        except subprocess.CalledProcessError:
            pass
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package_name, '--break-system-packages'])
        return True
    except subprocess.CalledProcessError:
        pass

def setup():
    config = configparser.ConfigParser()
    if not os.path.exists('files/config.ini'):
        config['app'] = {'is_setup_done': 'False'}
        with open('files/config.ini', 'w') as configfile:
            config.write(configfile)
    config.read('files/config.ini')
    is_setup_done = config.getboolean('app', 'is_setup_done')
    if not is_setup_done:
        if is_x_server_running():
            if not check_and_install_package('tk', 'python3-tk'):
                print("Failed to install tk.")
                sys.exit(1)
            if not check_and_install_package('pillow', 'python3-pil.imagetk'):
                print("Failed to install PIL.")
                sys.exit(1)
        if not check_and_install_package('flask', 'python3-flask'):
            print("Failed to install Flask.")
            sys.exit(1)
        if not check_and_install_package('pytube'):
            print("Failed to install PyTube.")
            sys.exit(1)
        if not check_and_install_package('mpv'):
            print("Failed to install mpv.")
            sys.exit(1)
        config.set('app', 'is_setup_done', 'True')
        with open('files/config.ini', 'w') as configfile:
            config.write(configfile)
setup()

from flask import Flask, render_template, request, redirect, url_for, jsonify
from pytube import Search, YouTube, innertube, Playlist
from pytube.innertube import _default_clients
from pytube.exceptions import AgeRestrictedError
import flask.cli, pytube.request

flask.cli.show_server_banner = lambda *args: None
logging.getLogger("werkzeug").disabled = True
pytube_logger = logging.getLogger('pytube')
pytube_logger.setLevel(logging.ERROR)
pytube.request.default_range_size = 1048576
innertube._cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files')
innertube._token_file = os.path.join(innertube._cache_dir, 'token.json')
innertube._default_clients["ANDROID"]["context"]["client"]["clientVersion"] = "19.08.35"
innertube._default_clients["IOS"]["context"]["client"]["clientVersion"] = "19.08.35"
innertube._default_clients["ANDROID_EMBED"]["context"]["client"]["clientVersion"] = "19.08.35"
innertube._default_clients["IOS_EMBED"]["context"]["client"]["clientVersion"] = "19.08.35"
innertube._default_clients["IOS_MUSIC"]["context"]["client"]["clientVersion"] = "6.41"
innertube._default_clients["ANDROID_MUSIC"] = _default_clients["ANDROID_CREATOR"]
template_dir = os.path.join(os.path.dirname(__file__), 'files')
app = Flask(__name__, template_folder=template_dir, static_url_path='', static_folder='files')
app.config['VIDEO_QUEUE'] = []
app.config['ready_for_new_queue'] = True
last_printed_status = ""

def is_x_server_running():
    try:
        subprocess.check_output(['pidof', 'Xorg'])
        return True
    except subprocess.CalledProcessError:
        return False
    
def authenticate_user():
    yt = YouTube('https://www.youtube.com/watch?v=TB7e8hI_Yew', use_oauth=True)
    title = yt.title
    logging.debug(f"{title}")

def backgroundset():
    if is_x_server_running():
        os.environ['DISPLAY'] = ':0'
        import tkinter as tk
        from PIL import Image, ImageTk
        backgrounds_dir = "./files/backgrounds/"
        background_files = [f for f in os.listdir(backgrounds_dir) if os.path.isfile(os.path.join(backgrounds_dir, f)) and f.endswith(('.png', '.jpg', '.jpeg', '.gif', '.PNG', '.JPG', '.JPEG', '.GIF'))]
        if background_files:
            selected_background = random.choice(background_files)
            selected_background_path = os.path.join(backgrounds_dir, selected_background)
            original_image = Image.open(selected_background_path)
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            resized_image = original_image.resize((screen_width, screen_height))
            background_image = ImageTk.PhotoImage(resized_image)
            if hasattr(backgroundset, 'background_label'):
                backgroundset.background_label.config(image=background_image)
                backgroundset.background_label.image = background_image
            else:
                backgroundset.background_label = tk.Label(root, image=background_image)
                backgroundset.background_label.place(x=0, y=0, relwidth=1, relheight=1)
                backgroundset.background_label.image = background_image
        else:
            root.configure(background='black')
            
def display_black_screen():
    if is_x_server_running():
        os.environ['DISPLAY'] = ':0'
        import tkinter as tk
        from PIL import Image, ImageTk
        global root
        root = tk.Tk()
        root.config(cursor='none')
        root.attributes('-fullscreen', True)
        backgroundset()
        font = ('Helvetica', 24)
        main_frame = tk.Frame(root, bg='black')
        main_frame.pack(expand=True)
        ip_eth0 = get_ip_address('eth0')
        ip_wlan0 = get_ip_address('wlan0')
        ip_address = ip_eth0 if ip_eth0 is not None else ip_wlan0
        label_ip = tk.Label(text=f"http://{ip_address if ip_address else 'Not available'}{':5000' if ip_address else ''}", fg="purple", bg="black", font=font)
        label_ip.pack(anchor='nw')
        title_frame = tk.Frame(main_frame, bg='black')
        title_frame.pack(expand=True)
        label = tk.Label(title_frame, text="No video playing", fg="white", bg="black", font=font)
        loading_label = tk.Label(title_frame, text="", fg="white", bg="black", font=font)
        label.grid(row=0, column=0, sticky='n', pady=(5, 0))
        loading_label.grid(row=1, column=0, sticky='n', pady=(5, 0))
        def update_text():
            if app.config.get('next_video_title'):
                next_video_title = app.config['next_video_title']
                label.config(text=next_video_title)
                progress_percentage = app.config.get('progress_percentage', 0)
                current_status = f"\nDownloading Progress: {progress_percentage:.0f}%\n"
                loading_label.config(text=current_status)
            else:
                label.config(text="No video playing")
                loading_label.config(text="")
            ip_eth0 = get_ip_address('eth0')
            ip_wlan0 = get_ip_address('wlan0')
            ip_address = ip_eth0 if ip_eth0 is not None else ip_wlan0
            label_ip.config(text=f"Address: http://{ip_address if ip_address else 'Not available'}{':5000' if ip_address else ''}")
            root.after(500, update_text)
        def update_background():
            backgroundset()
            root.after(60000, update_background)
        update_text()
        update_background()
        subprocess.run(['xset', 's', 'off'])
        subprocess.run(['xset', '-dpms'])    
        root.mainloop()
    else:
        print_status_to_console()
        
def extract_playlist_id(url):
    query = url.split('?')[1]
    params = query.split('&')
    for param in params:
        key, value = param.split('=')
        if key == 'list':
            return value
    return None

def get_ip_address(interface):
    try:
        result = subprocess.run(['ip', '-4', 'addr', 'show', interface], check=True, stdout=subprocess.PIPE)
        lines = result.stdout.decode().split('\n')
        for line in lines:
            if 'inet ' in line:
                ip = line.strip().split()[1].split('/')[0]
                return ip
        return None
    except subprocess.CalledProcessError:
        return None
    
def on_progress(stream, chunk, bytes_remaining):
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    progress_percentage = (bytes_downloaded / total_size) * 100 if total_size else 0
    app.config['progress_percentage'] = progress_percentage
    return progress_percentage

def play_video_from_queue():
    while app.config.get('is_playing', False):
        while app.config['VIDEO_QUEUE']:
            video_info = app.config['VIDEO_QUEUE'].pop(0)
            authenticate_user()
            app.config['next_video_title'] = f"{video_info['title']}"
            video_url = f'https://www.youtube.com/watch?v={video_info["video_id"]}'
            videopath = "/tmp/ytvid.mp4"
            app.config['progress_percentage'] = 0
            try:
                stream = YouTube(video_url, on_progress_callback=on_progress).streams.get_highest_resolution()
                stream.download(output_path="/tmp", filename="ytvid.mp4")
            except AgeRestrictedError as e:
                app.config['next_video_title'] = f"{video_info['title']}"
                stream = YouTube(video_url, use_oauth=True, on_progress_callback=on_progress).streams.get_highest_resolution()
                stream.download(output_path="/tmp", filename="ytvid.mp4")
            if is_x_server_running():
                backgroundset()
            process = subprocess.Popen([
                "mpv", "--fullscreen", "--no-border", "--ontop", "--no-terminal", videopath
            ], stderr=subprocess.DEVNULL)
            while True:
                if process.poll() is not None:
                    break
                time.sleep(1)
            app.config['next_video_title'] = None
            subprocess.Popen(["rm", "-rf", videopath])
        app.config['ready_for_new_queue'] = True
        break

def print_status_to_console():
    global last_printed_status
    while True:
        if app.config.get('next_video_title'):
            next_video_title = app.config['next_video_title']
            progress_percentage = app.config.get('progress_percentage', 0)
            current_status = f"\nTitle: {next_video_title}\nDownloading Progress: {progress_percentage:.1f}%\n"
        else:
            current_status = "\nNo video playing\n"
        ip_eth0 = get_ip_address('eth0')
        ip_wlan0 = get_ip_address('wlan0')
        ip_address = ip_eth0 if ip_eth0 is not None else ip_wlan0
        current_status += f"Address: http://{ip_address if ip_address else 'Not available'}{':5000' if ip_address else ''}\n"
        if current_status != last_printed_status:
            os.system('clear')
            print(current_status)
            last_printed_status = current_status

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        search_term = request.form['search_term']
        s = Search(search_term)
        if is_x_server_running() is False:
            print(f"Searching: {search_term}")
        if s.results:
            s.get_next_results()
            s.get_next_results()
            s.get_next_results()
            results_data = []
            for i, result in enumerate(s.results, start=1):
                result_data = {
                    "title": result.title,
                    "video_url": result.watch_url,
                }
                results_data.append(result_data)
            return render_template('index.html', results=results_data, app=app)
        else:
            return render_template('index.html', message='No search results found.', app=app)    
    return render_template('index.html', app=app)

@app.route('/add_to_queue', methods=['POST'])
def add_to_queue():
    video_url = request.form['video_url']
    if '&list=' in video_url and 'watch?v=' in video_url:
        playlist_id = extract_playlist_id(video_url)
        playlist_url = f'https://www.youtube.com/playlist?list={playlist_id}'
        playlist = Playlist(playlist_url)
        for video in playlist.videos:
            video_info = {
                'title': video.title,
                'video_id': video.video_id,
            }
            app.config['VIDEO_QUEUE'].append(video_info)
    elif '?list=' in video_url:
        playlist_id = extract_playlist_id(video_url)
        playlist_url = f'https://www.youtube.com/playlist?list={playlist_id}'
        playlist = Playlist(playlist_url)
        for video in playlist.videos:
            video_info = {
                'title': video.title,
                'video_id': video.video_id,
            }
            app.config['VIDEO_QUEUE'].append(video_info)
    else:
        yt = YouTube(video_url)
        video_info = {
            'title': yt.title,
            'video_id': yt.video_id,
        }
        app.config['VIDEO_QUEUE'].append(video_info)
    return redirect(url_for('index'))

@app.route('/close', methods=['POST'])
def close():
    if os.path.exists("/tmp/ytvid.mp4"):
        subprocess.Popen(["rm", "-rf", "/tmp/ytvid.mp4"])
    subprocess.run(["pkill", "mpv"])
    os.system('kill %d' % os.getpid())
    
@app.route('/clear', methods=['POST'])
def clear():
    app.config['VIDEO_QUEUE'] = []
    return redirect(url_for('index'))

@app.route('/get_queue')
def get_queue():
    queue_data = app.config['VIDEO_QUEUE']
    return jsonify(queue_data)

@app.route('/move_to_bottom', methods=['POST'])
def move_to_bottom():
    index = int(request.form['index'])
    if index >= 0 and index < len(app.config['VIDEO_QUEUE']) - 1:
        video = app.config['VIDEO_QUEUE'].pop(index)
        app.config['VIDEO_QUEUE'].append(video)
    return redirect(url_for('index'))

@app.route('/move_down', methods=['POST'])
def move_down():
    index = int(request.form['index'])
    if index >= 0 and index < len(app.config['VIDEO_QUEUE']) - 1:
        app.config['VIDEO_QUEUE'][index], app.config['VIDEO_QUEUE'][index + 1] = app.config['VIDEO_QUEUE'][index + 1], app.config['VIDEO_QUEUE'][index]
    return redirect(url_for('index'))

@app.route('/move_to_top', methods=['POST'])
def move_to_top():
    index = int(request.form['index'])
    if index > 0 and index < len(app.config['VIDEO_QUEUE']):
        video = app.config['VIDEO_QUEUE'].pop(index)
        app.config['VIDEO_QUEUE'].insert(0, video)
    return redirect(url_for('index'))

@app.route('/move_up', methods=['POST'])
def move_up():
    index = int(request.form['index'])
    if index > 0 and index < len(app.config['VIDEO_QUEUE']):
        app.config['VIDEO_QUEUE'][index], app.config['VIDEO_QUEUE'][index - 1] = app.config['VIDEO_QUEUE'][index - 1], app.config['VIDEO_QUEUE'][index]
    return redirect(url_for('index'))

@app.route('/play', methods=['POST', 'GET'])
def play():
    if not app.config.get('is_playing', False):
        app.config['is_playing'] = True
        threading.Thread(target=play_video_from_queue).start()
    elif app.config['ready_for_new_queue']:
        if not app.config['VIDEO_QUEUE']:
            app.config['is_playing'] = False
        else:
            app.config['ready_for_new_queue'] = False
            threading.Thread(target=play_video_from_queue).start()
    return redirect(url_for('index'))

@app.route('/queue', methods=['POST'])
def queue():
    video_url = request.form['video_url']
    yt = YouTube(video_url)
    video_info = {
        'title': yt.title,
        'video_id': yt.video_id,
    }
    app.config['VIDEO_QUEUE'].append(video_info)
    return redirect(url_for('index'))

@app.route('/remove', methods=['POST'])
def remove():
    index = int(request.form['index'])
    if 0 <= index < len(app.config['VIDEO_QUEUE']):
        removed_video = app.config['VIDEO_QUEUE'].pop(index)
        if app.config.get('next_video_title') == removed_video['title']:
            app.config['next_video_title'] = None
    return redirect(url_for('index'))

@app.route('/shuffle_queue', methods=['GET'])
def shuffle_queue():
    random.shuffle(app.config['VIDEO_QUEUE'])
    return redirect(url_for('index'))

@app.route('/skip', methods=['POST'])
def skip():
    try:
        if app.config.get('is_playing', False):
            subprocess.run(["pkill", "mpv"])
        return redirect(url_for('index'))
    except Exception as e:
        return f"An error occurred: {e}"

if __name__ == '__main__':
    authenticate_user()
    gui_thread = threading.Thread(target=display_black_screen)
    gui_thread.start()
    ip_eth0 = get_ip_address('eth0')
    ip_wlan0 = get_ip_address('wlan0')
    ip_address = ip_eth0 if ip_eth0 is not None else ip_wlan0
    print(f"Address: http://{ip_address if ip_address else 'Not available'}{':5000' if ip_address else ''}")
    app.run(host='0.0.0.0', port=5000, use_reloader=False)