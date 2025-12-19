from __future__ import annotations
from . import Plugin, WalkHelper

# References:
# https://07th-mod.github.io/ponscripter-fork/api/
# https://github.com/Galladite27/ONScripter-EN
class NScripter(Plugin):
    FUNCTIONS : set[str] = {"*define","*start","game","reset","definereset","end","*",";",":","%","$","?","~","/","{}","`","0x","^","setwindow","setwindow2","textoff","texton","windoweffect","erasetextwindow","btnnowindowerase","noteraseman","gettext","tateyoko","windowchip","setwindow3","textspeeddefault","font","defaultfont","!s","#","textclear","locate","puttext","br","textspeed","shadedistance","setkinsoku","addkinsoku","kinsoku","english","textcolor","language","@","\\","clickstr","linepage","_","clickvoice","autoclick","click","lrclick","clickskippage","setcursor","abssetcursor","mousecursor","mousemode","movemousecursor","getnextline","transmode","underline","bgalia","humanz","windowback","bg","ld","cl","tal","print","lsp","lsph","csp","vsp","spstr","msp","amsp","cell","blt","ofscpy","repaint","allsphide","allspresume","humanorder","humanpos","bgcopy","getspsize","getspmode","spfont","strsp","strsph","effect","effectblank","effectcut","effectskip","quake","quakex","quakey","monocro","nega","flushout","%","$","?","bar","barclear","prnum","prnumclear","cdfadeout","chkcdfile","chkcdfile_ex","mp3fadeout","play","playonce","playstop","wave","waveloop","wavestop","mp3","mp3loop","mp3save","dsound","dwave","dwaveloop","dwavestop","dwaveload","dwaveplay","dwaveplayloop","stop","mp3stop","mp3fadein","bgm","bgmonce","bgmstop","bgmfadeout","bgmfadein","loopbgm","loopbgmstop","mp3vol","chvol","voicevol","sevol","bgmvol","v","dv","mv","bgmdownmode","avi","mpegplay","movie","selectcolor","selectvoice","select","selgosub","selnum","goto","skip","gosub","return","jumpf","jumpb","tablegoto","trap","r_trap","lr_trap","trap2","lr_trap2","btndef","btn","btnwait","btnwait2","spbtn","cellcheckspbtn","getbtntimer","btntime","btntime2","exbtn","cellcheckexbtn","exbtn_d","transbtn","!d","!w","delay","wait","resettimer","waittimer","gettimer","spwait","stralias","numalias","intlimit","dim","mov","mov3","mov4","mov5","mov6","mov7","mov8","mov9","mov10","movl","add","+","sub","-","inc","dec","mul","*","div","/","mod","rnd","rnd2","itoa","itoa2","atoi","len","mid","split","sin","cos","tan","if","notif","cmp","fchk","lchk","for","next","break","rmenu","menusetwindow","savename","menuselectcolor","menuselectvoice","rlookback","rgosub","roff","rmode","lookbackbutton","lookbackcolor","lookbackvoice","lookbacksp","maxkaisoupage","lookbackflush","lookbackoff","lookbackon","kidokuskip","mode_wave_demo","skipoff","kidokumode","filelog","globalon","labellog","savenumber","savedir","loadgame","savegame","savegame2","getsavestr","savefileexist","saveon","saveoff","loadgosub","errorsave","autosaveoff","savepoint","mesbox","okcancelbox","yesnobox","inputstr","inputnum","input","textfield","clickpos","systemcall","fileexist","fileremove","labelexist","noloaderror","minimizewindow","automode","automode_time","defvoicevol","defsevol","defmp3vol","defbgmvol","mode_saya","mode_ext","mode800","mode400","mode320","value","gameid","soundpressplgin","spi","arc","nsa","nsadir","addnsadir","exec_dll","getret","setlayer","layermessage","versionstr","caption","date","time","savetime","getversion","getwindowsize","getreg","getini","readfile","killmenu","resetmenu","insertmenu","deletemenu","defaultspeed","!sd","menu_full","menu_window","isfull","menu_click_page","menu_click_def","menu_dwavvol","menu_waveon","menu_waveoff","*customsel","csel","cselbtn","cselgoto","getcselnum","getcselstr","nextcsel","selectbtnwait","textgosub","textbtnwait","getskipoff","getmouseover","checkkey","texec","texec2","getcursorpos","getcursorpos2","isskip","ispage","defsub","getparam","luacall","luasub","getscreenshot","savescreenshot","savescreenshot2","deletescreenshot","btnarea","btndown","isdown","getmousepos","spclclk","usewheel","useescspc","getcursor","getenter","gettab","getfunction","getpage","getinsert","getzxc","getmclick","()","rubyoff","rubyon","rubyon2","draw","drawclear","drawfill","drawbg","drawbg2","drawtext","drawsp","drawsp2","drawsp3","checkpage","getlog","logsp","logsp2","getlogtext","gettaglog","texthide","textshow","pretextgosub","[]","gettag","indent","pagetag","zenkakko","bmpcut","bw2a","bw2a3","chainbmp","createdummy","debuglog","shell","winexec","csvopen","csvread","csvwrite","csveof","csvclose","<>","linkcolor","textbtnstart","gettextbtnstr","erasetextbtn","textexbtn","textbtnoff","lsp2","lsph2","lsp2add","lsph2add","lsp2sub","lsph2sub","csp2","vsp2","msp2","amsp2","allsp2hide","allsp2resume","bclear","bsp","bdef","btime","bexec","bcursor","bdown","btrans","~","pmapfont","prendering","pfontstyle","pligate","pindentstr","pbreakstr","localestring","h_mapfont","h_rendering","h_fontstyle","h_ligate","h_indentstr","h_breakstr"}
    EXCLUDE : set[str] = {"bg", "btndef", "mp3loop"}
    
    def __init__(self : NScripter) -> None:
        super().__init__()
        self.name : str = "NScripter"
        self.description : str = " v1.1\nHandle NScripter scripts"
        self.related_tool_plugins : list[str] = [self.name]

    def get_setting_infos(self : NScripter) -> dict[str, list]:
        return {
            "nscripter_default_encoding": ["Select the default script encoding", "str", "shift_jis", ["auto"] + self.FILE_ENCODINGS],
            "nscripter_single_byte": ["Automatically set single byte mode", "bool", True, None],
        }

    def match(self : NScripter, file_path : str, is_for_action : bool) -> bool:
        return file_path.endswith(".nscript")

    # utility function for script commands
    def split_command(self : NScripter, string : str) -> list[str]:
        best = len(string)
        for c in (" ", "\t"):
            pos = string.find(c)
            if pos >= 0 and pos < best:
                best = pos
        if best == len(string):
            # check if it's single command with comment
            cmd = string.split(";")[0]
            if cmd in self.FUNCTIONS:
                return [cmd]
            return [string]
        else:
            return [string[:best], string[best+1:]]

    def force_single_byte(self : NScripter, string : str) -> str:
        if not string.startswith("`") and string != "" and ord(string[0]) <= 127:
            string = "`" + string.replace("@", "`@`") # https://kaisernet.org/onscripter/api/NScrAPI.html#_backquote
        return string

    def extract_string_from_cmd(self : NScripter, params : str) -> list[str]:
        strings : list[str] = []
        i = 0
        while i < len(params):
            if params[i] == '"':
                start = i
                while True:
                    i = params.find('"', i + 1)
                    if i == -1:
                        return strings
                    if params[i-1] != '\\':
                        break
                strings.append(params[start+1:i])
            elif params[i] == ';':
                break
            i += 1
        return strings

    def get_patched_string_from_cmd(self : NScripter, cmd : str, params : str, helper : WalkHelper) -> tuple[str, bool]:
        string = ""
        modified = False
        i = 0
        while i < len(params):
            if params[i] == '"':
                start = i
                while True:
                    i = params.find('"', i + 1)
                    if i == -1:
                        return "", False
                    if params[i-1] != '\\':
                        break
                tmp = helper.apply_string(params[start+1:i])
                if helper.str_modified:
                    string += '"' + tmp + '"'
                    modified = True
                else:
                    string += params[start:i+1]
            elif params[i] == ';':
                string += params[i:]
                break
            else:
                string += params[i]
            i += 1
        return cmd + " " + string, modified

    def read(self : NScripter, file_path : str, content : bytes) -> list[list[str]]:
        try:
            lines = content.decode(self.settings["nscripter_default_encoding"]).splitlines()
        except:
            lines = self.decode(content).splitlines()
        entries : list[list[str]] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.strip() != "" and not line.startswith((";", "*")):
                if line.endswith('\r'):
                    line = line[:-1]
                cmd = self.split_command(line)
                if len(cmd) > 1 and cmd[0].lower() in self.FUNCTIONS:
                    if cmd[0].lower() not in self.EXCLUDE:
                        group = [cmd[0]]
                        group.extend(self.extract_string_from_cmd(cmd[1].strip()))
                        if len(group) > 1:
                            entries.append(group)
                elif cmd[0].lower() in self.FUNCTIONS:
                    pass
                else:
                    group = ["Game String", line]
                    while i + 1 < len(lines):
                        i += 1
                        line = lines[i]
                        if line.endswith('\r'):
                            line = line[:-1]
                        if line.strip() == "" or line.startswith((";", "*")):
                            break
                        if self.split_command(line)[0].lower() in self.FUNCTIONS:
                            break
                        group.append(line)
                    entries.append(group)
            i += 1
        return entries

    def write(self : NScripter, name : str, file_path : str, content : bytes) -> tuple[bytes, bool]:
        helper : WalkHelper = WalkHelper(file_path, self.owner.strings[name])
        single_byte = self.settings["nscripter_single_byte"]
        try:
            lines = content.decode(self.settings["nscripter_default_encoding"]).splitlines()
            encoding = self.settings["nscripter_default_encoding"]
        except:
            lines = self.decode(content).splitlines()
            encoding = self.FILE_ENCODINGS[self._enc_cur_]
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.endswith('\r'):
                line = line[:-1]
                lines[i] = line
            if line.strip() != "" and not line.startswith((";", "*")):
                cmd = self.split_command(line)
                if len(cmd) > 1 and cmd[0].lower() in self.FUNCTIONS:
                    if cmd[0].lower() not in self.EXCLUDE:
                        tmp, changed = self.get_patched_string_from_cmd(cmd[0], cmd[1].strip(), helper)
                        if changed:
                            lines[i] = tmp
                elif cmd[0].lower() in self.FUNCTIONS:
                    pass
                else:
                    tmp = helper.apply_string(line)
                    if helper.str_modified:
                        lines[i] = self.force_single_byte(tmp) if single_byte else tmp
                    while i + 1 < len(lines):
                        i += 1
                        line = lines[i]
                        if line.endswith('\r'):
                            line = line[:-1]
                            lines[i] = line
                        if line.strip() == "" or line.startswith((";", "*")):
                            break
                        if self.split_command(line)[0].lower() in self.FUNCTIONS:
                            break
                        tmp = helper.apply_string(line)
                        if helper.str_modified:
                            lines[i] = self.force_single_byte(tmp) if single_byte else tmp
            i += 1
        if helper.modified:
            combined : str = "\r\n".join(lines)
            try:
                return combined.encode(encoding), True
            except Exception as e:
                se : str = str(e)
                if "codec can't encode character" in se:
                    try:
                        pos : int = int(se.split("in position ")[1].split(":")[0])
                        raise Exception(
                            "Invalid character for encoding '{}'. Part: '{}'".format(
                                encoding,
                                combined[max(0, pos - 10):pos + 10]
                            )
                        ) from e
                    except:
                        raise e
                else:
                    raise e
        return content, False