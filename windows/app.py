import importlib
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from saved_links import saved_url_file, load_saved_urls, filter_saved_urls, pick_saved_urls

SAVED_ROOT = Path(r'\\\\wsl.localhost\\Ubuntu\\home\\yannd\\.local\\share\\scrap-accounts')

RUNNER = r'''
import importlib, json, os, sys
from pathlib import Path
if os.getsid(0) != os.getpid(): os.setsid()
print('APP_PID=' + str(os.getpid()), flush=True)
platform, action, limit, metadata, comments_limit, thumbnails = sys.argv[1:]
base = Path.home() / '.local/share/scrap-accounts'
folder = base / platform
folder.mkdir(parents=True, exist_ok=True, mode=0o700)
os.chmod(base, 0o700)
profile = folder / 'browser'
urls = folder / 'urls.txt'
module = importlib.import_module({'Instagram':'scrap_insta.cli','X':'scrap_twitter.cli','YouTube':'scrap_youtube.cli'}[platform])
if action == 'import_urls':
    if platform != 'Instagram':
        raise SystemExit('L\'import direct d\'URLs est disponible pour Instagram.')
    from scrap_insta.urls import extract_urls_from_text
    from scrap_insta.files import load_urls_from_file, merge_url_lists, write_urls_to_file
    imported = extract_urls_from_text(sys.stdin.read())
    if not imported: raise SystemExit('Aucune URL de Reel ou de publication Instagram valide.')
    previous = load_urls_from_file(urls) if urls.exists() else []
    merged = merge_url_lists(previous, imported)
    write_urls_to_file(merged, urls)
    print(f'Ajout de {len(merged) - len(previous)} lien(s). Total : {len(merged)}', flush=True)
    raise SystemExit(0)
if action == 'scrape':
    args = ['scrape','--profile-dir',str(profile),'--output',str(urls),'--append','--limit',limit,'--stop-when-no-new','--unlimited-scrolls']
    if platform != 'Instagram': args += ['--source-page','manual']
    sys.argv = ['scrap-accounts'] + args
    code = module.main()
    if code: raise SystemExit(code)
    print('Liens enregistrés : ' + str(urls), flush=True)
elif action in ('download', 'download_selected'):
    if action == 'download' and not urls.exists():
        raise SystemExit('Aucun lien enregistré. Utilise la bibliothèque ou importe un fichier.')
    from playwright.sync_api import sync_playwright
    import tempfile
    with tempfile.TemporaryDirectory(prefix='scrap-batch-') as tmp:
        input_file = urls
        if action == 'download_selected':
            selected = list(dict.fromkeys(line.strip() for line in sys.stdin.read().splitlines() if line.strip()))
            if not selected:
                raise SystemExit('Aucun lien sélectionné.')
            input_file = Path(tmp) / 'selection.txt'
            input_file.write_text('\\n'.join(selected) + '\\n', encoding='utf-8')
            input_file.chmod(0o600)
            print(f'Téléchargement des {len(selected)} liens sélectionnés.', flush=True)
        cookies_file = Path(tmp) / 'cookies.txt'
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(str(profile), headless=True)
            cookies = ctx.cookies()
            ctx.close()
        with cookies_file.open('w') as f:
            f.write('# Netscape HTTP Cookie File\n')
            for c in cookies:
                domain = c['domain']
                expires = max(0, int(c.get('expires', 0)))
                f.write('\t'.join([domain, str(domain.startswith('.')).upper(), c['path'], str(c['secure']).upper(), str(expires), c['name'], c['value']]) + '\n')
        os.chmod(cookies_file, 0o600)
        args = ['download','--input',str(input_file),'--output-dir',str(folder / 'downloads'),'--cookies-file',str(cookies_file),'--comments-limit',comments_limit]
        if metadata == '1': args += ['--metadata-only']
        if thumbnails == '1' and metadata != '1': args += ['--write-thumbnail']
        sys.argv = ['scrap-accounts'] + args
        raise SystemExit(module.main())
'''

CREATE_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

class App:
    def __init__(self, root):
        self.root = root
        self.proc = None
        self.pid = None
        self.events = queue.Queue()
        root.title('Scrap Accounts')
        root.geometry('1080x900')
        root.minsize(940, 700)
        root.configure(bg='#10131b')
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', background='#10131b', foreground='#e8edf6', font=('Segoe UI', 10))
        style.configure('TFrame', background='#10131b')
        style.configure('Card.TFrame', background='#1a2030')
        style.configure('Card.TLabel', background='#1a2030')
        style.configure('Muted.TLabel', foreground='#9aa9c1')
        style.configure('TButton', padding=(16,11), background='#28334a', foreground='#edf2ff', borderwidth=0)
        style.map('TButton', background=[('active','#364663'),('disabled','#1d2534')], foreground=[('disabled','#627088')])
        style.configure('Primary.TButton', background='#7661ed', foreground='white')
        style.map('Primary.TButton', background=[('active','#8b78ff'),('disabled','#2b2945')], foreground=[('disabled','#7d769f')])
        style.configure('TCombobox', fieldbackground='#263149', background='#263149', foreground='#edf2ff', arrowcolor='#b7c5dc', padding=8)
        style.map('TCombobox', fieldbackground=[('readonly','#263149')], foreground=[('readonly','#edf2ff')])
        style.configure('TSpinbox', fieldbackground='#263149', background='#263149', foreground='#edf2ff', arrowcolor='#b7c5dc', padding=8)
        style.configure('TCheckbutton', background='#1a2030', foreground='#b8c5db', padding=4)
        style.map('TCheckbutton', background=[('active','#1a2030')])
        style.configure('Horizontal.TProgressbar', troughcolor='#222c40', background='#8b78ff', borderwidth=0)
        root.option_add('*TCombobox*Listbox.background', '#263149')
        root.option_add('*TCombobox*Listbox.foreground', '#edf2ff')
        sidebar = tk.Frame(root, bg='#171c28', width=200)
        sidebar.pack(side='left', fill='y')
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text='S / A', bg='#171c28', fg='#a695ff', font=('Segoe UI',28,'bold')).pack(anchor='w', padx=25, pady=(30,0))
        tk.Label(sidebar, text='SCRAP ACCOUNTS', bg='#171c28', fg='#e8edf6', font=('Segoe UI',10,'bold')).pack(anchor='w', padx=25, pady=(5,35))
        tk.Label(sidebar, text='  ↓   Ma collection', bg='#292440', fg='#cfc5ff', font=('Segoe UI',11), padx=14, pady=12).pack(fill='x', padx=14)
        tk.Label(sidebar, text='Tes réseaux\nTa bibliothèque', justify='left', bg='#171c28', fg='#91a0b9', font=('Segoe UI',11), pady=25).pack(anchor='w', padx=25)
        tk.Label(sidebar, text='LOCAL & PERSONNEL\nSessions conservées\nsur cet ordinateur', justify='left', bg='#171c28', fg='#8190aa', font=('Segoe UI',9), pady=28).pack(side='bottom', anchor='w', padx=25)
        main = ttk.Frame(root, padding=(24,16))
        main.pack(side='left', fill='both', expand=True)
        ttk.Label(main, text='TA BIBLIOTHÈQUE SOCIALE', foreground='#a695ff', font=('Segoe UI',9,'bold')).pack(anchor='w')
        ttk.Label(main, text='Garde ce qui t’inspire.', font=('Segoe UI',25,'bold')).pack(anchor='w', pady=(6,5))
        ttk.Label(main, text='Retrouve tes liens, vidéos et souvenirs dans une collection locale.', style='Muted.TLabel').pack(anchor='w', pady=(0,10))
        self.tabs = ttk.Notebook(main)
        self.tabs.pack(fill='both', expand=True)
        library = ttk.Frame(self.tabs, padding=12)
        collect = ttk.Frame(self.tabs, padding=12)
        self.tabs.add(library, text='Mes liens enregistrés')
        self.tabs.add(collect, text='Récupérer des liens')
        card = ttk.Frame(collect, style='Card.TFrame', padding=20)
        card.pack(fill='x')
        ttk.Label(card, text='01  /  Choisis ta source', style='Card.TLabel', font=('Segoe UI',12,'bold')).pack(anchor='w', pady=(0,13))
        row = ttk.Frame(card, style='Card.TFrame')
        row.pack(fill='x')
        self.platform = tk.StringVar(value='Instagram')
        self.choice = ttk.Combobox(row, textvariable=self.platform, values=['Instagram','X','YouTube'], state='readonly', width=18)
        self.choice.pack(side='left')
        ttk.Label(row, text='    Maximum de liens  ', style='Card.TLabel').pack(side='left')
        self.limit = tk.StringVar(value='100')
        ttk.Spinbox(row, from_=1, to=10000, textvariable=self.limit, width=7).pack(side='left')
        self.metadata = tk.BooleanVar(value=False)
        ttk.Checkbutton(card, text='Métadonnées uniquement — sans les médias', variable=self.metadata).pack(anchor='w', pady=(12,0))
        comment_row = ttk.Frame(card, style='Card.TFrame')
        comment_row.pack(fill='x', pady=(9,0))
        ttk.Label(comment_row, text='Commentaires max par publication  ', style='Card.TLabel').pack(side='left')
        self.comments_limit = tk.StringVar(value='100')
        ttk.Spinbox(comment_row, from_=0, to=1000, textvariable=self.comments_limit, width=7).pack(side='left')
        self.thumbnails = tk.BooleanVar(value=True)
        ttk.Checkbutton(card, text='Télécharger aussi les miniatures', variable=self.thumbnails).pack(anchor='w', pady=(4,0))
        ttk.Label(card, text='Les commentaires Instagram ne sont pas toujours fournis ; le rapport distingue les données manquantes.', style='Muted.TLabel', wraplength=630).pack(anchor='w', pady=(6,0))
        ttk.Label(collect, text='02  /  Ou colle directement tes liens Instagram', font=('Segoe UI',12,'bold')).pack(anchor='w', pady=(15,6))
        self.pasted_urls = tk.Text(collect, height=3, bg='#151b27', fg='#e8edf6', insertbackground='#e8edf6', relief='flat', padx=10, pady=8, wrap='word', font=('Consolas',10))
        self.pasted_urls.pack(fill='x')
        self.import_button = ttk.Button(collect, text='Ajouter les liens à ma collection', command=lambda:self.start('import_urls'))
        self.import_button.pack(anchor='w', pady=(8,4))
        ttk.Label(collect, text='03  /  Ou récupère les liens depuis le navigateur', font=('Segoe UI',12,'bold')).pack(anchor='w', pady=(14,6))
        ttk.Label(collect, text='Ouvre le navigateur, affiche la page souhaitée, puis clique sur Commencer.', style='Muted.TLabel', wraplength=670).pack(anchor='w')
        buttons = ttk.Frame(collect)
        buttons.pack(fill='x', pady=16)
        self.scrape = ttk.Button(buttons, text='Ouvrir le navigateur', style='Primary.TButton', command=lambda:self.start('scrape'))
        self.scrape.pack(side='left')
        self.go = ttk.Button(buttons, text='Commencer', style='Primary.TButton', command=self.proceed, state='disabled')
        self.go.pack(side='left', padx=6)
        self.stop = ttk.Button(buttons, text='Arrêter', command=self.cancel, state='disabled')
        self.stop.pack(side='left', padx=6)

        ttk.Label(library, text='Les liens collectés restent disponibles entre les sessions.', font=('Segoe UI',11)).pack(anchor='w', pady=(1,10))
        library_source = ttk.Frame(library)
        library_source.pack(fill='x', pady=(0,9))
        ttk.Label(library_source, text='Réseau :').pack(side='left', padx=(0,8))
        self.library_choice = ttk.Combobox(library_source, textvariable=self.platform, values=['Instagram','X','YouTube'], state='readonly', width=16)
        self.library_choice.pack(side='left')
        self.refresh_button = ttk.Button(library_source, text='Actualiser', command=self.refresh_links)
        self.refresh_button.pack(side='left', padx=10)
        self.import_file_button = ttk.Button(library_source, text='Importer un fichier .txt', command=self.import_url_file)
        self.import_file_button.pack(side='left')

        self.link_search = tk.StringVar()
        self.link_search.trace_add('write', lambda *_: self.filter_links())
        search_row = ttk.Frame(library)
        search_row.pack(fill='x', pady=(0,8))
        ttk.Label(search_row, text='Rechercher dans les liens :').pack(side='left', padx=(0,9))
        ttk.Entry(search_row, textvariable=self.link_search).pack(side='left', fill='x', expand=True)

        list_frame = ttk.Frame(library)
        list_frame.pack(fill='both', expand=True)
        self.saved_list = tk.Listbox(list_frame, selectmode='extended', exportselection=False,
                                     bg='#151b27', fg='#e8edf6', selectbackground='#50468f',
                                     font=('Consolas',10), relief='flat', activestyle='none',
                                     height=12)
        scroll = ttk.Scrollbar(list_frame, orient='vertical', command=self.saved_list.yview)
        self.saved_list.configure(yscrollcommand=scroll.set)
        self.saved_list.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
        self.saved_list.bind('<<ListboxSelect>>', lambda _: self.update_links_summary())
        self.all_links = []
        self.visible_links = []
        self.links_summary = tk.StringVar(value='Aucun lien chargé.')
        ttk.Label(library, textvariable=self.links_summary, style='Muted.TLabel').pack(anchor='w', pady=(8,8))
        actions = ttk.Frame(library)
        actions.pack(fill='x')
        self.download = ttk.Button(actions, text='Télécharger tous les liens enregistrés', style='Primary.TButton',
                                   command=lambda:self.start('download'))
        self.download.pack(side='left')
        self.download_selected_button = ttk.Button(actions, text='Télécharger la sélection',
                                                    command=self.download_selection)
        self.download_selected_button.pack(side='left', padx=7)
        ttk.Label(library, text='Ctrl ou Maj pour sélectionner plusieurs lignes. Les médias déjà récupérés seront ignorés par l’archive.', style='Muted.TLabel',
                  wraplength=650).pack(anchor='w', pady=(9,0))
        self.choice.bind('<<ComboboxSelected>>', lambda _: self.refresh_links())
        self.library_choice.bind('<<ComboboxSelected>>', lambda _: self.refresh_links())
        self.root.after(200, self.refresh_links)
        self.status = tk.StringVar(value='Prêt')
        ttk.Label(main, textvariable=self.status, foreground='#b7aaff', wraplength=680).pack(anchor='w', pady=(0,8))
        self.progress = ttk.Progressbar(main, mode='indeterminate')
        self.progress.pack(fill='x', pady=(0,16))
        ttk.Label(main, text='ACTIVITÉ', style='Muted.TLabel', font=('Segoe UI',9,'bold')).pack(anchor='w', pady=(0,8))
        self.log = tk.Text(main, font=('Consolas',10), bg='#151b27', fg='#afbed5', insertbackground='#afbed5', relief='flat', borderwidth=0, padx=14, pady=12, wrap='word', state='disabled', height=5)
        self.log.pack(fill='both', expand=True)
        ttk.Button(main, text='Ouvrir mes fichiers', command=self.open_files).pack(anchor='e', pady=(12,0))
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(100, self.poll)
        self.append('Bienvenue. Choisis un réseau pour démarrer ta collection.\n')

    def append(self, text):
        self.log.configure(state='normal')
        self.log.insert('end', text)
        self.log.see('end')
        self.log.configure(state='disabled')

    def refresh_links(self):
        try:
            self.all_links = load_saved_urls(saved_url_file(SAVED_ROOT, self.platform.get()), self.platform.get())
            self.links_error = ''
        except (OSError, UnicodeError, ValueError) as exc:
            self.all_links = []
            self.links_error = f'Liste inaccessible : {exc}'
        self.import_file_button.configure(state='normal' if self.platform.get() == 'Instagram' and self.proc is None else 'disabled')
        self.filter_links()

    def filter_links(self):
        self.visible_links = filter_saved_urls(self.all_links, self.link_search.get())
        self.saved_list.delete(0, 'end')
        for url in self.visible_links:
            self.saved_list.insert('end', url)
        self.update_links_summary()

    def update_links_summary(self):
        if getattr(self, 'links_error', ''):
            self.links_summary.set(self.links_error)
        else:
            self.links_summary.set(
                f'{len(self.all_links)} liens sauvegardés | '
                f'{len(self.visible_links)} affichés | '
                f'{len(self.saved_list.curselection())} sélectionnés'
            )
        ready = self.proc is None
        self.download.configure(state='normal' if ready and self.all_links else 'disabled')
        self.download_selected_button.configure(
            state='normal' if ready and self.saved_list.curselection() else 'disabled'
        )

    def download_selection(self):
        urls = pick_saved_urls(self.visible_links, tuple(self.saved_list.curselection()))
        if not urls:
            messagebox.showinfo('Sélection', 'Sélectionne au moins un lien dans la liste.')
            return
        self.start('download_selected', '\n'.join(urls))

    def import_url_file(self):
        if self.proc is not None or self.platform.get() != 'Instagram':
            return
        path = filedialog.askopenfilename(
            title='Importer une extraction Instagram',
            filetypes=[('Fichiers texte', '*.txt'), ('Tous les fichiers', '*.*')],
        )
        if not path:
            return
        try:
            raw = Path(path).read_text(encoding='utf-8-sig')
        except (OSError, UnicodeError) as exc:
            messagebox.showerror('Import impossible', str(exc))
            return
        self.start('import_urls', raw)

    def start(self, action, input_text=None):
        if self.proc is not None: return
        try:
            limit = int(self.limit.get())
            comments_limit = int(self.comments_limit.get())
            if not 1 <= limit <= 10000 or not 0 <= comments_limit <= 1000: raise ValueError()
        except ValueError:
            messagebox.showerror('Options invalides', 'Liens : 1-10 000. Commentaires : 0-1 000.')
            return
        if action == 'import_urls' and input_text is None:
            input_text = self.pasted_urls.get('1.0', 'end-1c')
        if action in ('import_urls', 'download_selected') and not (input_text or '').strip():
            messagebox.showinfo('Liens manquants', 'Ajoute ou sélectionne des URL avant de continuer.')
            return
        if action == 'download' and not self.all_links:
            messagebox.showinfo('Aucun lien', 'Aucune URL sauvegardée pour ce réseau.')
            return
        self.pid = None
        self.active_action = action
        self.progress.start(12)
        self.scrape.configure(state='disabled')
        self.download.configure(state='disabled')
        self.download_selected_button.configure(state='disabled')
        self.refresh_button.configure(state='disabled')
        self.import_file_button.configure(state='disabled')
        self.import_button.configure(state='disabled')
        self.choice.configure(state='disabled')
        self.library_choice.configure(state='disabled')
        self.status.set('Ouverture…' if action == 'scrape' else 'Import des liens…' if action == 'import_urls' else 'Téléchargement de la sélection…' if action == 'download_selected' else 'Téléchargement des liens sauvegardés…')
        args = ['wsl.exe','-d','Ubuntu','--exec','/home/yannd/scrap_accounts/.venv/bin/python','-u','-c',RUNNER,self.platform.get(),action,str(limit),'1' if self.metadata.get() else '0',str(comments_limit),'1' if self.thumbnails.get() else '0']
        try:
            self.proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', creationflags=CREATE_NO_WINDOW)
        except OSError as e:
            self.append(str(e)+'\n')
            self.finish(-1)
            return
        self.stop.configure(state='normal')
        if action in ('import_urls', 'download_selected'):
            try:
                self.proc.stdin.write(input_text)
                self.proc.stdin.close()
            except OSError as exc:
                self.append(str(exc) + '\n')
        def read():
            proc = self.proc
            # Read characters because input() does not end its prompt with a newline.
            buf = ''
            for char in iter(lambda:proc.stdout.read(1), ''):
                buf += char
                if char == '\n' or 'Press Enter to start scraping the active page...' in buf:
                    self.events.put(('line',buf))
                    buf = ''
            if buf: self.events.put(('line',buf))
            self.events.put(('done', proc.wait()))
        threading.Thread(target=read, daemon=True).start()

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == 'done': self.finish(value)
                elif value.startswith('APP_PID='): self.pid = int(value.split('=')[1])
                else:
                    self.append(value)
                    if 'Press Enter to start scraping' in value:
                        self.go.configure(state='normal')
                        self.status.set('Connecte-toi dans le navigateur, puis clique sur Commencer.')
        except queue.Empty: pass
        self.root.after(100, self.poll)

    def proceed(self):
        if self.proc:
            try:
                self.proc.stdin.write('\n')
                self.proc.stdin.flush()
                self.go.configure(state='disabled')
                self.status.set('Récupération des liens…')
            except (OSError, ValueError): pass

    def finish(self, code):
        self.progress.stop()
        self.proc = None
        self.pid = None
        self.go.configure(state='disabled')
        self.stop.configure(state='disabled')
        self.scrape.configure(state='normal')
        self.refresh_button.configure(state='normal')
        self.import_button.configure(state='normal')
        self.choice.configure(state='readonly')
        self.library_choice.configure(state='readonly')
        self.status.set('Terminé' if code == 0 else 'Opération interrompue ou en erreur — voir le journal.')
        self.refresh_links()

    def cancel(self):
        if self.pid:
            subprocess.run(['wsl.exe','-d','Ubuntu','--exec','/bin/kill','-TERM','--','-'+str(self.pid)], creationflags=CREATE_NO_WINDOW, capture_output=True)
        elif self.proc: self.proc.terminate()

    def close(self):
        if self.proc:
            if not messagebox.askyesno('Fermer', 'Arrêter l’opération et fermer ?'): return
            self.cancel()
        self.root.destroy()

    def open_files(self):
        path = '\\\\wsl.localhost\\Ubuntu\\home\\yannd\\.local\\share\\scrap-accounts'
        try: os.startfile(path)
        except OSError: messagebox.showinfo('Mes fichiers', 'Le dossier sera créé lors de la première opération.')

if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    if '--self-test' in sys.argv:
        root.update()
        assert app.platform.get() == 'Instagram'
        root.destroy()
        print('Interface OK')
    else: root.mainloop()
