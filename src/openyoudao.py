#!/usr/bin/python
#coding=utf8
#Author : eleven.i386
#Email  : eleven.i386@gmail.com
#Site   : eleveni386.7axu.com
#Date   : 15-04-10
#DES	: 有道划词翻译

import requests
import json
import time
import gtk
import webkit
import Xlib.display as display
from pyxhook import pyxhook
import threading
import urllib
import dbm
import gobject

def HotKey(func):
    AltF8 = 74
    def kbevent( event ):
        if event.ScanCode == 74:
            func()
    
    hookman = pyxhook.HookManager()
    hookman.KeyDown = kbevent
    hookman.HookKeyboard()
    hookman.start()

def get_pos():
    ds = display.Display()
    pos = ds.screen().root.query_pointer()._data
    return (pos['root_x'], pos['root_y'])

def Html_Template(**keys):
    template = open('template.html', 'r').read().format
    _css = open('css.css','r').read()
    basic_list = keys['basic']
    p = keys['phonetic']
    web = keys['web']
    t = keys['query']
    basic_html = ''
    web_html = ''
    m = '<a id="more" href="http://dict.youdao.com/search?keyfrom=selector&q=%s" target="_blank" hidefocus="true">详细>></a>'%t
    for b in basic_list:
        basic_html += '<p>%s</p>\n'%b
    for w in web:
        web_html += '<span class="web-item">%s</span>\n<span class="split"></span>\n'%w
    if len(t) >= 40: t = ''; m = ''
    return template(title=t, basic= basic_html, 
            web = web_html, phonetic=p, css= _css,
            more = m)

class YouDaoTranslateApi():
    def __init__(self):
        self.URI='http://fanyi.youdao.com/openapi.do?type=data&doctype=jsonp&version=1.1&relatedUrl=http://fanyi.youdao.com/&keyfrom=fanyiweb&key=null&callback=YoudaoSelector.Instance.update&translate=on&{q}&ts={ts}'.format
        Home = os.environ['HOME']
        openyoudaopath = os.path.join(Home, '.openyoudao')
        self.dbpath = os.path.join(openyoudaopath, 'youdaocache')
        if not os.path.exists(openyoudaopath):
            try:
                os.mkdir(openyoudaopath)
            except IOError as e:
                print e
                sys.exit(1)

    def query(self, word):
        result = {}
        r = self.local_query(word)
        if r:
            o = r
        else:
            o = self.internet_query(word)

        result['query'] = o['query']
        if o.has_key('basic'):
            result['basic'] = o['basic']['explains']
            phonetic = o['basic'].get('phonetic', '')
        else:
            result['basic'] = o.get('translation','')
            phonetic = ''
        if phonetic:
            result['phonetic'] = '[ %s ]'%phonetic
        else:
            result['phonetic'] = phonetic
        if o.has_key('web'):
            result['web'] = o['web'][0]['value']
        else:
            result['web'] = ''
        return result

    def internet_query(self, word):
        result = {}
        t = int(time.time())
        url = self.URI(q=urllib.urlencode({'q':word}), ts=t)
        r = requests.get(url)
        o = json.loads(r.text.replace('YoudaoSelector.Instance.update', '').replace('(', '').replace(')', '').replace(';',''))
        self.cache_query(word, o)
        return o

    def local_query(self,word):
        try:
            r = dbm.open(self.dbpath, 'c')
            return eval(r[word])
        except:
            return None
        r.close()

    def cache_query(self, query, ask):
        r = dbm.open(self.dbpath, 'c')
        r[query] = str(ask)
        r.close()

class View():
    def __init__(self):
        self.view = webkit.WebView()
        self.view.connect('hovering-over-link', self.link_hover)
        self.view.connect('button-press-event', self.link_click)
        self.sw = gtk.ScrolledWindow()
        self.sw.add(self.view)
        self.sw.hide()
        self. url = ''

    def open_html(self, html):
        self.view.load_html_string(html,'')
        self.view.show_all()

    def return_obj(self):
        return self.sw

    def link_hover(self, title, url, data):
        self.url = data

    def link_click(self, widget, event):
        import webbrowser
        webbrowser.open(self.url)


class youdao_translate_UI():

    def __init__(self):
        self.flags = True
        self.v = View()
        self.pixbuf = gtk.gdk.pixbuf_new_from_file('./youdao.png')
        self.pixbuf_stop = gtk.gdk.pixbuf_new_from_file('./youdao_stop.png')
        self.pixbuf_disconnect = gtk.gdk.pixbuf_new_from_file('./youdao_disconnect.png')
        self.statusicon = gtk.StatusIcon()
        self.statusicon.set_from_pixbuf(self.pixbuf)
        self.statusicon.connect("popup-menu", self.right_click_event)
        self.clip = gtk.clipboard_get(gtk.gdk.SELECTION_PRIMARY)
        self.clip.connect("owner-change", self._clipboard_changed)
        self.w = gtk.Window()
        self.w.connect('destroy', gtk.main_quit)
        self.w.connect('focus_out_event',self.Hide)
        self.w.set_size_request(320, 158)
        self.w.set_decorated(False)
        vbox = gtk.VBox(True, 0)
        vbox.pack_start(self.v.return_obj())
        self.w.add(vbox)
        # 按键监听, 全局热键 Ctrl+F8
        t = threading.Thread(target=HotKey, args=(self.huaci_event,))
        t.setDaemon(True)
        t.start()
        gobject.timeout_add(1000, self.is_online)

    def _clipboard_changed(self,clipboard, event):
        if self.flags:
            text = clipboard.wait_for_text()
            yd = YouDaoTranslateApi()
            r = yd.query(text.strip())
            self.v.open_html(Html_Template(**r))
            self.Show()
        else:
            pass

    def Hide(self, widget, event):
        self.w.hide_all()

    def Show(self):
        x, y = get_pos()
        self.w.move(x, y)
        self.w.show_all()

    def right_click_event(self, icon, button, time):

        self.menu = gtk.Menu()
        huaci = gtk.MenuItem()
        if self.flags:
            huaci.set_label("关闭划词")
        else:
            huaci.set_label("开启划词")
        quit = gtk.MenuItem()
        quit.set_label("退出")
        huaci.connect("activate", self.huaci_event)
        quit.connect("activate", gtk.main_quit)
        self.menu.append(huaci)
        self.menu.append(quit)

        self.menu.show_all()
        self.menu.popup(None, None, gtk.status_icon_position_menu, button,time, self.statusicon)

    def huaci_event(self, widget=None):
        if self.flags:
            self.flags = False
            self.statusicon.set_from_pixbuf(self.pixbuf_stop)
        else:
            self.flags = True
            self.statusicon.set_from_pixbuf(self.pixbuf)

    def is_online(self):
        try:
            r = requests.get('http://fanyi.youdao.com')
            if r.status_code == 200:
                self.flags = True
                self.statusicon.set_from_pixbuf(self.pixbuf)
            else:
                self.flags = False
                self.statusicon.set_from_pixbuf(self.pixbuf_disconnect)
        except:
            self.flags = False
            self.statusicon.set_from_pixbuf(self.pixbuf_disconnect)
        #print time.time()
        return True

    def Loop(self):
        gtk.main()
        

if __name__ == '__main__':
    import os, sys
    pid = os.fork()
    if pid == 0:
        translate_UI = youdao_translate_UI()
        translate_UI.Loop()
    else:
        sys.exit(0)
