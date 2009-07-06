# vim:fileencoding=utf-8

#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

#   Copyright (c) 2009 by Paweł Tomak <satherot (at) gmail (dot) com>

import ekg
import glib
import time
import pynotify
import re
import sys

TIMEOUT_STATUS=3500
TIMEOUT_MSG=3500

def removeHTML(text):
    reg = re.compile("&")
    text = reg.sub("&#38;", text)
    reg = re.compile("<")
    text = reg.sub("&#60;", text)
    reg = re.compile(">")
    text = reg.sub("&#62;", text)
    return text

def catchURL(text):
    reg = re.compile("(http://[^ ]+|www.[^ ]+)")
    if len(reg.findall(text)):
        text = reg.sub(r'<a href="\1">\1</a>', text)
        return [1, text]
    else:
        return [0, text]

def transStatus(status):
    return {
            'avail': 'dostepny',
            'away': 'zaraz wracam',
            'blocking': 'BLOKUJE',
            'error': 'BLAD STATUSU!!',
            'ffc': 'chetny do rozmowy',
            'chat': 'chetny do rozmowy',
            'dnd': 'nie przeszkadzac',
            'xa': 'bardzo zajety',
            'notavail': 'niedostepny',
            }[status]

def displayNotify(title, text, timeout, type):
    if not pynotify.init("EkgNotif"):
        ekg.echo("you don't seem to have pynotify installed")
        return 0
    if ekg.config["notify:catch_url"] != "0":
        l = catchURL(text)
        if l[0]:
            text = l[1]
            timeout = int(ekg.config["notify:catch_url_time"])
    n = pynotify.Notification(title, text, type)
    n.set_timeout(timeout)

    # Most probably glib.GError is:
    # The name org.freedesktop.Notifications was not provided by any .service files
    # Catch this exception and print information in debug window. Sometimes I
    # do not have org.freedesktop.Notifications registered and I do not want
    # error messages in chat window.
    try:
        n.show()
    except e as glib.GError:
        ekg.debug("pynotif: " + str(e))

    return 1

def notifyStatus(session, uid, status, descr):
    if ekg.config["notify:status_notify"] == "0":
        return 1
    regexp = re.compile('irc:*')
    regexp = regexp.findall(session)
    if len(regexp):
        return 1
    regexp = re.compile('.*' + session + '.*')
    regexp = regexp.findall(uid)
    if len(regexp):
        ekg.echo("Zmienil sie status sesji: %s. Nie zostal on zmieniony przez ten program. Sprawdz to, jesli nie zmieniales statusu jakims innym programem" % session)
        return 1
    sesja = ekg.session_get(session)
    regexp = re.compile('([a-z]{2,4}:[^/]+)')
    regexp = regexp.match(uid)
    regexp = regexp.group()
    try:
        user = sesja.user_get(regexp)
    except KeyError:
        ekg.echo("Nie znalazlem uzytkownika %s." % uid)
        return 1
    status = transStatus(status)
    nick = user.nickname or user.uid or "Empty"
    s = status or "Empty"
    s = removeHTML(s)
    text = "<b>" + nick + "</b> zmienil status na <b>" + s + "</b>"
    if descr:
        descr = removeHTML(descr)
        text = text + ":\n" + descr + "\n"
    return displayNotify(session, text, TIMEOUT_STATUS, ekg.config["notify:icon_status"])

def notifyMessage(session, uid, type, text, stime, ignore_level):
    if ekg.config["notify:message_notify"] == "0":
        return 1
    regexp = re.compile('irc:*')
    regexp = regexp.findall(session)
    if len(regexp):
        return 1
    text = removeHTML(text)
    sesja = ekg.session_get(session)
    try:
        user = sesja.user_get(uid)
    except KeyError:
        ekg.echo("Nie znalazlem uzytkownika %s." % uid)
        return 1
    t = time.strftime("%H:%M:%S", time.gmtime(stime))
    title = t + " " + user.nickname
    if len(text) > 200:
        text = text[0:199] + "... >>>\n\n"
    return displayNotify(title, text, TIMEOUT_MSG, ekg.config["notify:icon_msg"])

def timeCheck(name, args):
    global TIMEOUT_MSG
    global TIMEOUT_STATUS
    rexp = re.compile('^[0-9]{4,4}')
    rexp = rexp.findall(args)
    if len(rexp) == 1:
        if name == "notify:message_timeout":
            TIMEOUT_MSG = int(rexp[0])
            return 1
        if name == "notify:status_timeout":
            TIMEOUT_STATUS = int(rexp[0])
            return 1
        if name == "notify:catch_url_timeout":
            return 1

    if name == "notify:message_timeout":
        ekg.echo("Zmienna %s bedzie pomijana do czasu, az zostanie ustawiona wartosc z zakresu od 1000ms do 9999ms. Jej obecna wartosc to: %i" % (name,TIMEOUT_MSG))
    elif name == "notify:status_timeout":
        ekg.echo("Zmienna %s bedzie pomijana do czasu, az zostanie ustawiona wartosc z zakresu od 1000ms do 9999ms. Jej obecna wartosc to: %i" % (name,TIMEOUT_STATUS))
    elif name == "notify:catch_url_timeout":
        ekg.echo("Zmienna %s bedzie pomijana do czasu, az zostanie ustawiona wartosc z zakresu od 1000ms do 9999ms. Jej obecna wartosc to: %i" % (name,TIMEOUT_STATUS))
    return 0

ekg.handler_bind('protocol-status', notifyStatus)
ekg.handler_bind("protocol-message-received", notifyMessage)
ekg.variable_add("notify:icon_status", "dialog-warning")
ekg.variable_add("notify:icon_msg", "dialog-warning")
ekg.variable_add("notify:message_timeout", "3500", timeCheck)
ekg.variable_add("notify:message_notify", "1")
ekg.variable_add("notify:status_timeout", "3500", timeCheck)
ekg.variable_add("notify:status_notify", "1")
ekg.variable_add("notify:catch_url", "1")
ekg.variable_add("notify:catch_url_timeout", "5000", timeCheck)

if int(ekg.config["notify:message_timeout"]) < 1000 or int(ekg.config["notify:message_timeout"]) > 9999:
    timeCheck("notify:message_timeout", ekg.config["notify:message_timeout"])
if int(ekg.config["notify:status_timeout"]) < 1000 or int(ekg.config["notify:status_timeout"]) > 9999:
    timeCheck("notify:status_timeout", ekg.config["notify:status_timeout"])

