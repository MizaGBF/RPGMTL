
var intervals = []; // on screen notifications
// main parts
var bar = null;
var main = null;
var bottom = null;
// global variables
var keypressenabled = false;
var path = null;
var prjname = null;
var prj = null;
var prjdata = null;
var prjversion = 0;
var prjstring = null;
var prjlist = null;
var currentstr = null;
var strtablecache = [];
var lastfileopened = null;
var laststringsearch = null;
var laststringinteracted = 0;

// entry point
function init()
{
	// register the main elements
	bar = document.getElementById("top");
	main = document.getElementById("main");
	bottom = document.getElementById("bottom");
	// request the project list
	postAPI("/api/main", project_list);
}

document.onkeypress = function (e) {
	if(keypressenabled)
	{
		if(e.code == 'Space' && strtablecache.length > 0 && e.target.tagName != "textarea")
		{
			if(e.ctrlKey && !e.shiftKey)
			{
				let i = (laststringinteracted + 1) % strtablecache.length;
				while(i != laststringinteracted)
				{
					if(!strtablecache[i][0].classList.contains("disabled") && strtablecache[i][2].classList.contains("disabled"))
					{
						laststringinteracted = i;
						strtablecache[i][0].scrollIntoView();
						break;
					}
					i = (i + 1) % strtablecache.length;
				}
				e.stopPropagation();
			}
			else if(!e.ctrlKey && e.shiftKey)
			{
				let i = (laststringinteracted + 1) % strtablecache.length;
				while(i != laststringinteracted)
				{
					if(strtablecache[i][2].classList.contains("disabled"))
					{
						laststringinteracted = i;
						strtablecache[i][0].scrollIntoView();
						break;
					}
					i = (i + 1) % strtablecache.length;
				}
				e.stopPropagation();
			}
		}
	}
};

// create and add a new element to a node, and return it
function addTo(node, tagName, {cls = [], id = null, onload = null, onclick = null, onerror = null, br = true}={})
{
	let tag = document.createElement(tagName);
	for(let i = 0; i < cls.length; ++i)
		tag.classList.add(cls[i]);
	if(id) tag.id = id;
	if(onload) tag.onload = onload;
	if(onclick) tag.onclick = onclick;
	if(onerror) tag.onerror = onerror;
	if(node) node.appendChild(tag);
	if(br) node.appendChild(document.createElement("br"));
	return tag;
}

// set the loading element visibility
function set_loading(state)
{
	if(state)
	{
		document.getElementById("loader-animation").classList.add("loader");
		document.getElementById("loading").style.display = null;
	}
	else
	{
		document.getElementById("loader-animation").classList.remove("loader");
		document.getElementById("loading").style.display = "none";
	}
}

// set the loading element text
function set_loading_text(content)
{
	document.getElementById("loader-text").innerHTML = content;
}

// make a GET request
// About callbacks:
// success is called on success
// failure is called on failure
function getAPI(url, success = null, failure = null)
{
	reqAPI("GET", url, success, failure);
}

// make a POST request
function postAPI(url, success = null, failure = null, payload = null)
{
	reqAPI("POST", url, success, failure, payload);
}

// process requests
function reqAPI(type, url, success, failure, payload = null)
{
	set_loading(true);
	var xhr = new XMLHttpRequest();
	xhr.ontimeout = function () {
		processAPI.apply(xhr, [success, failure]);
	};
	xhr.onload = function() {
		if (xhr.readyState === 4) {
			processAPI.apply(xhr, [success, failure]);
		}
	};
	xhr.open(type, url, true);
	xhr.timeout = 0; // no timeout
	if(type == "POST" && payload != null)
	{
		xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
		xhr.send(JSON.stringify(payload));
	}
	else
	{
		xhr.send(null);
	}
}

// display a popup with the given string for 2.5s
function pushPopup(string)
{
	let div = document.createElement('div');
	div.className = 'popup';
	div.innerHTML = string;
	document.body.appendChild(div);
	intervals.push(setInterval(rmPopup, 4000, div));
}

// remove a popup
function rmPopup(popup)
{
	popup.parentNode.removeChild(popup);
	clearInterval(intervals[0]);
	intervals.shift();
}

// clear the main area
function clearMain()
{
	set_loading(false);
	main.innerHTML = "";
	return document.createDocumentFragment();
}

// update the main area with a fragment
function updateMain(fragment)
{
	main.appendChild(fragment);
}

// clear the top bar area
function clearBar()
{
	bar.innerHTML = '';
	return document.createDocumentFragment();
}

// update the top bar area with a fragment
function updateBar(fragment)
{
	bar.appendChild(fragment);
}

// generitc function to process the result of requests
function processAPI(success, failure)
{
	try
	{
		let json = JSON.parse(this.response);
		if("message" in json)
			pushPopup(json["message"]);
		if(json["result"] == "ok")
		{
			if("name" in json["data"] && "config" in json["data"])
			{
				prjname = json["data"]["name"];
				prj = json["data"]["config"];
				prjversion = prj["version"];
			}
			if(success)
				success(json["data"]);
			else
				set_loading(false);
		}
		else
		{
			if(failure)
				failure(json);
			else
				set_loading(false);
		}
		set_loading_text("Waiting RPGMTL response...");
	}
	catch(err)
	{
		console.error("Exception thrown", err.stack);
		set_loading_text("An unexpected error occured.<br>" + err.stack + "<br><br>Refresh the page.<br>Make sure to report the bug if the issue continue.");
	}
}

// handle result of /project_list
function project_list(data)
{
	// Reset
	keypressenabled = null;
	path = null;
	prjname = null;
	prj = null;
	prjdata = null;
	prjversion = 0;
	prjstring = null;
	prjlist = null;
	currentstr = null;
	trtablecache = null;
	lastfileopened = null;
	laststringsearch = null;
	
	// top bar
	let fragment = clearBar();
	addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
		if(this.classList.contains("selected") || window.event.ctrlKey)
			postAPI("/api/shutdown", function(_unused_) {
				clearBar();
				let fragment = clearMain();
				addTo(fragment, "div", {cls:["title"]}).innerHTML = "RPGMTL has been shutdown";
				updateMain(fragment);
			});
		else
		{
			this.classList.add("selected");
			pushPopup("Press again to confirm.");
		}
	}}).innerHTML = '<img src="assets/images/shutdown.png">';
	addTo(fragment, "div", {cls:["inline"], br:false}).innerHTML = 'RPGMTL v' + data["verstring"];
	addTo(fragment, "div", {cls:["barfill"], br:false});
	addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
		document.getElementById("help").innerHTML = "<ul>\
			<li>Load an existing <b>Project</b> or create a new one.</li>\
			<li>Click twice on the Shutdown button to stop RPGMTL remotely.</li>\
		</ul>";
		document.getElementById("help").style.display = "";
	}}).innerHTML = '<img src="assets/images/help.png">';
	updateBar(fragment);
	
	// main part
	fragment = clearMain();
	addTo(fragment, "div", {cls:["title"]}).innerHTML = "Project List";
	if(data["list"].length > 0)
	{
		for(let i = 0; i < data["list"].length; ++i)
		{
			const t = data["list"][i];
			addTo(fragment, "div", {cls:["interact"], onclick:function(){
				postAPI("/api/open_project", project_menu, project_fail, {"name":t});
			}}).innerHTML = data["list"][i];
		}
	}
	addTo(fragment, "div", {cls:["title"]});
	addTo(fragment, "div", {cls:["interact"], onclick:function(){
		set_loading_text("Select the Game in the opened dialog.");
		postAPI("/api/update_location", new_project);
	}}).innerHTML = '<img src="assets/images/new.png">New Project';
	addTo(fragment, "div", {cls:["interact"], onclick:function(){
		postAPI("/api/settings", setting_menu);
	}}).innerHTML = '<img src="assets/images/setting.png">Global Settings';
	addTo(fragment, "div", {cls:["interact"], onclick:function(){
		postAPI("/api/translator", translator_menu);
	}}).innerHTML = '<img src="assets/images/translate.png">Default Translator';
	updateMain(fragment);
}

// display settings
function setting_menu(data)
{
	try
	{
		const is_project = "config" in data;
		// top bar
		let fragment = clearBar();
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			if(is_project)
				project_menu();
			else
				postAPI("/api/main", project_list);
		}}).innerHTML = '<img src="assets/images/back.png">';
		addTo(fragment, "div", {cls:["inline"], br:false}).innerHTML = is_project ? prjname + " Settings" : "Default Settings";
		addTo(fragment, "div", {cls:["barfill"], br:false});
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			document.getElementById("help").innerHTML = "<ul>\
				<li>Some settings might require you to extract your project strings again, be careful to not lose progress.</li>\
				<li><b>Default</b> Settings are your projects defaults.</li>\
				<li><b>Project</b> Settings override <b>Default</b> Settings when modified.</li>\
			</ul>";
			document.getElementById("help").style.display = "";
		}}).innerHTML = '<img src="assets/images/help.png">';
		updateBar(fragment);
		
		// main part
		fragment = clearMain();
		let layout = data["layout"];
		let settings = data["settings"];
		
		if(is_project)
		{
			addTo(fragment, "div", {cls:["interact"], onclick:function(){
				postAPI("/api/update_settings", function(result_data) {
					pushPopup("The Project Settings have been reset to Global Settings.");
					project_menu();
				}, null, {name:prjname});
			}}).innerHTML = '<img src="assets/images/trash.png">Reset All Settings';
		}
		
		let count = 0;
		for(const [file, fsett] of Object.entries(layout))
		{
			addTo(fragment, "div", {cls:["title", "left"], br:false}).innerHTML = file + " Plugin settings";
			if(file in data["descriptions"] && data["descriptions"][file] != "")
				addTo(fragment, "div", {cls:["left", "interact-group", "smalltext"]}).innerText = data["descriptions"][file];
			for(const [key, fdata] of Object.entries(fsett))
			{
				switch(fdata[1])
				{
					case "bool": // bool type
					{
						addTo(fragment, "div", {cls:["settingtext"], br:false}).innerHTML = fdata[0];
						const elem = addTo(fragment, "div", {cls:["interact", "button"], onclick:function(){
							let callback = function(result_data) {
								pushPopup("The setting has been updated.");
								set_loading(false);
								if(key in result_data["settings"])
									elem.classList.toggle("green", result_data["settings"][key]);
							};
							if(is_project)
								postAPI("/api/update_settings", callback, null, {name:prjname, key:key, value:!elem.classList.contains("green")});
							else
								postAPI("/api/update_settings", callback, null, {key:key, value:!elem.classList.contains("green")});
						}});
						elem.innerHTML = '<img src="assets/images/confirm.png">';
						if(key in settings)
							elem.classList.toggle("green", settings[key]);
						++count;
						break;
					}
					default: // other types
					{
						addTo(fragment, "div", {cls:["settingtext"]}).innerHTML = fdata[0];
						if(fdata[2] == null) // text input
						{
							const input = addTo(fragment, "input", {cls:["input", "smallinput"], br:false});
							input.type = "text";
							const elem = addTo(fragment, "div", {cls:["interact", "button"], onclick:function(){
								let val = "";
								switch(fdata[1])
								{
									case "int":
										if(isNaN(input.value) || isNaN(parseFloat(input.value)))
										{
											pushPopup("The value isn't a valid integer.");
											return;
										}
										val = Math.floor(parseFloat(input.value));
										break;
									case "float":
										if(isNaN(input.value) || isNaN(parseFloat(input.value)))
										{
											pushPopup("The value isn't a valid floating number.");
											return;
										}
										val = parseFloat(input.value);
										break;
									default:
										val = input.value;
										break;
								}
								let callback = function(result_data) {
									pushPopup("The setting has been updated.");
									set_loading(false);
									if(key in result_data["settings"])
										input.value = result_data["settings"][key];
								};
								if(is_project)
									postAPI("/api/update_settings", callback, null, {name:prjname, key:key, value:val});
								else
									postAPI("/api/update_settings", callback, null, {key:key, value:val});
							}});
							elem.innerHTML = '<img src="assets/images/confirm.png">';
							input.addEventListener('keypress', function(event) {
								if (event.key === 'Enter')
								{
									event.preventDefault();
									elem.click();
								}
							});
							
							if(key in settings)
								input.value = settings[key];
							++count;
						}
						else // choice selection
						{
							const sel = addTo(fragment, "select", {cls:["input", "smallinput"], br:false});
							for(let i = 0; i < fdata[2].length; ++i)
							{
								let opt = addTo(sel, "option");
								opt.value = fdata[2][i];
								opt.textContent = fdata[2][i];
							}
							const elem = addTo(fragment, "div", {cls:["interact", "button"], onclick:function()
							{
								let callback = function(result_data) {
									pushPopup("The setting has been updated.");
									set_loading(false);
									if(key in result_data["settings"])
										set.value = result_data["settings"][key];
								};
								if(is_project)
									postAPI("/api/update_settings", callback, null, {name:prjname, key:key, value:sel.value});
								else
									postAPI("/api/update_settings", callback, null, {key:key, value:sel.value});
							}});
							elem.innerHTML = '<img src="assets/images/confirm.png">';
							if(key in settings)
								sel.value = settings[key];
							++count;
						}
						break;
					}
				}
			}
		}
		if(count == 0)
			addTo(fragment, "div", {cls:["title", "left"]}).innerHTML = "No settings available for your Plugins";
		updateMain(fragment);
	}
	catch(err)
	{
		console.error("Exception thrown", err.stack);
		pushPopup("An unexpected error occured.");
		postAPI("/api/main", project_list);
	}
}

// translator pick menu
function translator_menu(data)
{
	try
	{
		const is_project = "config" in data;
		// top bar
		let fragment = clearBar();
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			if(is_project)
				project_menu();
			else
				postAPI("/api/main", project_list);
		}}).innerHTML = '<img src="assets/images/back.png">';
		addTo(fragment, "div", {cls:["inline"], br:false}).innerHTML = is_project ? prjname + " Settings" : "Global Settings";
		addTo(fragment, "div", {cls:["barfill"], br:false});
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			document.getElementById("help").innerHTML = "<ul>\
				<li>Select the Translator Plugin to use.</li>\
				<li><b>Default</b> Translator is used by default.</li>\
				<li><b>Project</b> Translator override the <b>Default</b> when modified.</li>\
			</ul>";
			document.getElementById("help").style.display = "";
		}}).innerHTML = '<img src="assets/images/help.png">';
		updateBar(fragment);
		
		// main part
		fragment = clearMain();
		let list = data["list"];
		let current = data["current"];
		if(list.length == 0)
		{
			addTo(fragment, "div", {cls:["title", "left"]}).innerHTML = "No Translator Plugin available";
		}
		else
		{
			if(is_project)
			{
				addTo(fragment, "div", {cls:["interact"], onclick:function(){
					postAPI("/api/update_translator", function(result_data) {
						pushPopup("The Project Translator have been reset to the default.");
						project_menu();
					}, null, {name:prjname});
				}}).innerHTML = '<img src="assets/images/trash.png">Use RPGMTL Default';
			}
			
			const sel = addTo(fragment, "select", {cls:["input", "smallinput"], br:false});
			for(let i = 0; i < list.length; ++i)
			{
				let opt = addTo(sel, "option");
				opt.value = list[i];
				opt.textContent = list[i];
			}
			const elem = addTo(fragment, "div", {cls:["interact", "button"], onclick:function()
			{
				let callback = function(result_data) {
					pushPopup("The setting has been updated.");
					set_loading(false);
					if(key in result_data["settings"])
						set.value = result_data["settings"][key];
				};
				if(is_project)
					postAPI("/api/update_translator", callback, null, {name:prjname, value:sel.value});
				else
					postAPI("/api/update_translator", callback, null, {value:sel.value});
			}});
			elem.innerHTML = '<img src="assets/images/confirm.png">';
			sel.value = current;
		}
		updateMain(fragment);
	}
	catch(err)
	{
		console.error("Exception thrown", err.stack);
		pushPopup("An unexpected error occured.");
		postAPI("/api/main", project_list);
	}
}

// new project creation
function new_project(data)
{
	if(data["path"] == "" || data["path"] == null)
	{
		postAPI("/api/main", project_list);
	}
	else
	{
		path = data["path"];
		// top bar
		let fragment = clearBar();
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			postAPI("/api/main", project_list);
		}}).innerHTML = '<img src="assets/images/back.png">';
		addTo(fragment, "div", {cls:["inline"], br:false}).innerHTML = 'Create a new Project';
		addTo(fragment, "div", {cls:["barfill"], br:false});
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			document.getElementById("help").innerHTML = "<ul>\
				<li>The Project Name has little importance, just make sure you know what it refers to.</li>\
				<li>If already taken, a number will be added after the name.</li>\
			</ul>";
			document.getElementById("help").style.display = "";
		}}).innerHTML = '<img src="assets/images/help.png">';
		updateBar(fragment);
		
		// main part
		fragment = clearMain();
		addTo(fragment, "div", {cls:["title", "left"]}).innerHTML = "Folder/Project Name";
		
		let input = addTo(fragment, "input", {cls:["input"]});
		input.type = "text";
		
		let tmp = path.split("/");
		if(tmp.length >= 1)
			input.value = tmp[tmp.length-1];
		else
			input.value = "Project";
		
		addTo(fragment, "div", {cls:["interact"], onclick:function(){
			set_loading_text("Creating the project...");
			if(input.value.trim() != "")
				postAPI("/api/new_project", project_menu, project_fail, {path: path, name: input.value});
		}}).innerHTML = '<img src="assets/images/confirm.png">Create';
		updateMain(fragment);
	}
}

// fallback if a critical error occured
function project_fail()
{
	postAPI("/api/main", project_list);
}

// display project options
function project_menu(data = null)
{
	try
	{
		// top bar
		let fragment = clearBar();
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			postAPI("/api/main", project_list);
		}}).innerHTML = '<img src="assets/images/back.png">';
		addTo(fragment, "div", {cls:["inline"], br:false}).innerHTML = prjname;
		addTo(fragment, "div", {cls:["barfill"], br:false});
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			document.getElementById("help").innerHTML = "<ul>\
				<li><b>Browse Files</b> to browse and translate strings.</li>\
				<li><b>Add a Fix</b> to add Python patches to apply during the release process (Check the README for details).</li>\
				<li>Set your <b>Settings before<b/> extracting the strings.</li>\
			</ul>\
			<ul>\
				<li><b>Update the Game Files</b> if it got updated or if you need to re-copy the files.</li>\
				<li><b>Extract the Strings</b> if you need to extract them from Game Files.</li>\
				<li><b>Release a Patch</b> to create a copy of Game files with your translated strings. They will be found in the <b>release</b> folder.</li>\
			</ul>\
			<ul>\
				<li><b>Import Strings from older RPGMTL</b> to import strings from an older RPGMTL file format.</li>\
				<li><b>Strings Backups</b> to open the list of backups if you need to revert the project data to an earlier state.</li>\
			</ul>";
			document.getElementById("help").style.display = "";
		}}).innerHTML = '<img src="assets/images/help.png">';
		updateBar(fragment);
		
		// main part
		fragment = clearMain();
		addTo(fragment, "div", {cls:["title"]}).innerHTML = prjname;
		addTo(fragment, "div", {cls:["title", "left"]}).innerHTML = "Game Folder: " + prj["path"];
		if(prj.files)
		{
			addTo(fragment, "div", {cls:["interact"], onclick:function(){
				postAPI("/api/browse", browse_files, null, {name:prjname, path:""});
			}}).innerHTML = '<img src="assets/images/folder.png">Browse Files';
			addTo(fragment, "div", {cls:["interact"], onclick:function(){
				postAPI("/api/patches", browse_patches, null, {name:prjname});
			}}).innerHTML = '<img src="assets/images/bandaid.png">Add a Fix';
		}
		addTo(fragment, "div", {cls:["interact"], onclick:function(){
			postAPI("/api/settings", setting_menu, null, {name:prjname});
		}}).innerHTML = '<img src="assets/images/setting.png">Project Settings';
		addTo(fragment, "div", {cls:["interact"], onclick:function(){
			postAPI("/api/translator", translator_menu, null, {name:prjname});
		}}).innerHTML = '<img src="assets/images/translate.png">Project Translator';
		addTo(fragment, "div", {cls:["spacer"]});
		addTo(fragment, "div", {cls:["interact"], onclick:function(){
			set_loading_text("Select the Game in the opened dialog to update the project files.");
			postAPI("/api/update_location", project_menu, project_fail, {name:prjname});
		}}).innerHTML = '<img src="assets/images/update.png">Update the Game Files';
		addTo(fragment, "div", {cls:["interact"], onclick:function(){
			set_loading_text("Extracting, be patient...");
			postAPI("/api/extract", project_menu, project_fail, {name:prjname});
		}}).innerHTML = '<img src="assets/images/export.png">Extract the Strings';
		if(prj.files)
		{
			addTo(fragment, "div", {cls:["interact"], onclick:function(){
				postAPI("/api/release", project_menu, null, {name:prjname});
			}}).innerHTML = '<img src="assets/images/release.png">Release a Patch';
			addTo(fragment, "div", {cls:["spacer"]});
			addTo(fragment, "div", {cls:["interact"], onclick:function(){
				postAPI("/api/backups", backup_list, null, {name:prjname});
			}}).innerHTML = '<img src="assets/images/copy.png">String Backups';
			addTo(fragment, "div", {cls:["interact"], onclick:function(){
				postAPI("/api/import", project_menu, null, {name:prjname});
			}}).innerHTML = '<img src="assets/images/import.png">Import Strings from older RPGMTL';
			addTo(fragment, "div", {cls:["spacer"]});
		}
		updateMain(fragment);
	}
	catch(err)
	{
		console.error("Exception thrown", err.stack);
		pushPopup("An unexpected error occured.");
		postAPI("/api/main", project_list);
	}
}

function addSearchBar(node, bp, defaultVal = null)
{
	const input = addTo(node, "input", {cls:["input", "smallinput"], br:false});
	input.placeholder = "Search a string";
	if(defaultVal != null)
		input.value = defaultVal;
	else if(laststringsearch != null)
		input.value = laststringsearch;
	else
		input.value = "";
	const button = addTo(node, "div", {cls:["interact", "button"], onclick:function(){
		if(input.value != "")
		{
			laststringsearch = input.value;
			postAPI("/api/search_string", string_search, null, {name:prjname, path:bp, search:laststringsearch});
		}
	}});
	button.innerHTML = '<img src="assets/images/search.png">';
	input.addEventListener('keypress', function(event) {
		if (event.key === 'Enter')
		{
			event.preventDefault();
			button.click();
		}
	});
}

// open folder
function browse_files(data)
{
	try
	{
		keypressenabled = false;
		laststringsearch = null;
		const bp = data["path"];
		// top bar
		let fragment = clearBar();
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function() {
			let returnpath = bp.includes('/') ? bp.split('/').slice(0, bp.split('/').length-2).join('/')+'/' : "";
			if(bp == "")
				project_menu();
			else
			{
				if(returnpath == '/') returnpath = '';
				postAPI("/api/browse", browse_files, null, {name:prjname, path:returnpath});
			}
		}}).innerHTML = '<img src="assets/images/back.png">';
		addTo(fragment, "div", {cls:["inline"], br:false}).innerHTML = "Path: " + bp;
		addTo(fragment, "div", {cls:["barfill"], br:false});
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			document.getElementById("help").innerHTML = "<ul>\
				<li>CTRL+Click on a file to <b>disable</b> it, it won't be patched during the release process.</li>\
				<li>The string counts and completion percentages update slowly in the background, don't take them for granted.</li>\
			</ul>";
			document.getElementById("help").style.display = "";
		}}).innerHTML = '<img src="assets/images/help.png">';
		updateBar(fragment);
		
		// main part
		fragment = clearMain();
		addTo(fragment, "div", {cls:["title"]}).innerHTML = prjname;
		addSearchBar(fragment, bp);
		
		let completion = addTo(fragment, "div", {cls:["title", "left"]});
		let fstring = 0;
		let ftotal = 0;
		let fcount = 0;
		
		addTo(fragment, "div", {cls:["title", "left"]}).innerHTML = bp;
		for(let i = 0; i < data["folders"].length; ++i)
		{
			const t = data["folders"][i];
			let div = addTo(fragment, "div", {cls:["interact"]});
			if(t == "..") div.innerHTML = '<img src="assets/images/back.png">..';
			else div.innerHTML = '<img src="assets/images/folder.png">' + t;
			div.onclick = function()
			{
				if(t == "..")
				{
					let s = bp.split("/");
					if(s.length == 2)
						postAPI("/api/browse", browse_files, null, {name:prjname, path:""});
					else
						postAPI("/api/browse", browse_files, null, {name:prjname, path:s.slice(0, s.length-2).join("/") + "/"});
				}
				else
					postAPI("/api/browse", browse_files, null, {name:prjname, path:t});
			};
		}
		addTo(fragment, "div", {cls:["title", "left"]}).innerHTML = "List of Files";
		let cls = [
			["interact"],
			["interact", "disabled"]
		];
		let scrollTo = null;
		for(const [key, value] of Object.entries(data["files"]))
		{
			let button = addTo(fragment, "div", {cls:cls[+value], br:false, id:"text:"+key, onclick:function(){
				if(window.event.ctrlKey)
				{
					postAPI("/api/ignore_file", update_file_list, null, {name:prjname, path:key, state:+!this.classList.contains("disabled")});
				}
				else
				{
					set_loading_text("Opening " + key + "...");
					postAPI("/api/file", open_file, null, {name:prjname, path:key});
				}
			}});
			let total = prj["files"][key]["strings"] - prj["files"][key]["disabled_strings"];
			let count = prj["files"][key]["translated"];
			let percent = total > 0 ? ", " + (Math.round(10000 * count / total) / 100) + "%)" : ")";
			
			if(!value)
			{
				fstring += prj["files"][key]["strings"];
				ftotal += total;
				fcount += count;
			}
			
			if(count == total)
				button.classList.add("complete");
			button.innerHTML = key + ' (' + prj["files"][key]["strings"] + percent;
			if(key == lastfileopened)
				scrollTo = button;
		}
		let percent = ftotal > 0 ? ', ' + (Math.round(10000 * fcount / ftotal) / 100) + '%' : '';
		completion.innerHTML = "Current Total: " + fstring + " strings" + percent;
		updateMain(fragment);
		if(scrollTo != null)
			scrollTo.scrollIntoView();
		lastfileopened = null;
	}
	catch(err)
	{
		lastfileopened = null;
		console.error("Exception thrown", err.stack);
		pushPopup("An unexpected error occured.");
		project_menu();
	}
}

// search a string
function string_search(data)
{
	try
	{
		const bp = data["path"];
		// top bar
		let fragment = clearBar();
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function() {
			postAPI("/api/browse", browse_files, null, {name:prjname, path:data["path"]});
		}}).innerHTML = '<img src="assets/images/back.png">';
		addTo(fragment, "div", {cls:["inline"], br:false}).innerHTML = "Search Results";
		addTo(fragment, "div", {cls:["barfill"], br:false});
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			document.getElementById("help").innerHTML = "<ul>\
				<li>Your search results are displayed here.</li>\
			</ul>";
			document.getElementById("help").style.display = "";
		}}).innerHTML = '<img src="assets/images/help.png">';
		updateBar(fragment);
		
		// main part
		fragment = clearMain();
		addTo(fragment, "div", {cls:["title"]}).innerHTML = prjname;
		addSearchBar(fragment, bp, data["search"]);
		
		addTo(fragment, "div", {cls:["title", "left"]}).innerHTML = "Search Results";
		let cls = [
			["interact"],
			["interact", "disabled"]
		];
		for(const [key, value] of Object.entries(data["files"]))
		{
			let button = addTo(fragment, "div", {cls:cls[+value], br:false, id:"text:"+key, onclick:function(){
				if(window.event.ctrlKey)
				{
					postAPI("/api/ignore_file", update_file_list, null, {name:prjname, path:key, state:+!this.classList.contains("disabled")});
				}
				else
				{
					set_loading_text("Opening " + key + "...");
					postAPI("/api/file", open_file, null, {name:prjname, path:key});
				}
			}});
			let total = prj["files"][key]["strings"] - prj["files"][key]["disabled_strings"];
			let count = prj["files"][key]["translated"];
			let percent = total > 0 ? ', ' + (Math.round(10000 * count / total) / 100) + '%)' : ')';
			button.innerHTML = key + ' (' + total + " strings" + percent;
		}
		updateMain(fragment);
	}
	catch(err)
	{
		console.error("Exception thrown", err.stack);
		pushPopup("An unexpected error occured.");
		project_menu();
	}
}

// open fix list
function browse_patches(data)
{
	try
	{
		// top part
		let fragment = clearBar();
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			project_menu();
		}}).innerHTML = '<img src="assets/images/back.png">';
		addTo(fragment, "div", {cls:["inline"], br:false}).innerHTML = prjname;
		addTo(fragment, "div", {cls:["barfill"], br:false});
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			document.getElementById("help").innerHTML = "<ul>\
				<li>Select an existing patch/fix or create a new one.</li>\
				<li>The patch/fix will be applied on all files whose name contains the patch/fix name.</li>\
				<li>The patch/fix code must be valid <b>Python</b> code, refer to the <b>README</b> for details.</li>\
			</ul>";
			document.getElementById("help").style.display = "";
		}}).innerHTML = '<img src="assets/images/help.png">';
		updateBar(fragment);
		
		// main part
		fragment = clearMain();
		addTo(fragment, "div", {cls:["title"]}).innerHTML = prjname;
		addTo(fragment, "div", {cls:["title", "left"]}).innerHTML = "Fix List";
		for(const [key, value] of Object.entries(prj["patches"]))
		{
			addTo(fragment, "div", {cls:["interact"], onclick:function()
			{
				postAPI("/api/open_patch", edit_patch, null, {name:prjname, key:key});
			}
			}).innerHTML = '<img src="assets/images/bandaid.png">' + key;
		}
		addTo(fragment, "div", {cls:["spacer"]});
		addTo(fragment, "div", {cls:["interact"], onclick:function(){
			edit_patch({});
		}}).innerHTML = '<img src="assets/images/new.png">Create';
		updateMain(fragment);
	}
	catch(err)
	{
		console.error("Exception thrown", err.stack);
		pushPopup("An unexpected error occured.");
		project_menu();
	}
}

// edit a fix
function edit_patch(data)
{
	try
	{
		const key = data["key"];
		// top bar
		let fragment = clearBar();
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			postAPI("/api/patches", browse_patches, null, {name:prjname});
		}}).innerHTML = '<img src="assets/images/back.png">';
		addTo(fragment, "div", {cls:["inline"], br:false}).innerHTML = "Create a Fix";
		addTo(fragment, "div", {cls:["barfill"], br:false});
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			document.getElementById("help").innerHTML = "<ul>\
				<li>Select an existing patch/fix or create a new one.</li>\
				<li>The patch/fix will be applied on all files whose name contains the patch/fix name.</li>\
				<li>The patch/fix code must be valid <b>Python</b> code, refer to the <b>README</b> for details.</li>\
			</ul>";
			document.getElementById("help").style.display = "";
		}}).innerHTML = '<img src="assets/images/help.png">';
		updateBar(fragment);
		
		// main part
		fragment = clearMain();
		addTo(fragment, "div", {cls:["title"]}).innerHTML = prjname;
		addTo(fragment, "div", {cls:["title", "left"]}).innerHTML = "Filename match";
		addTo(fragment, "input", {cls:["input"], id:"filter"}).type = "text";
		addTo(fragment, "div", {cls:["title", "left"]}).innerHTML = "Fix Code";
		addTo(fragment, "div", {cls:["input"], id:"fix"}).contentEditable = "plaintext-only";
		addTo(fragment, "div", {cls:["interact"], onclick:function(){
			if(document.getElementById("fix").textContent.trim() != "")
				postAPI("/api/update_patch", browse_patches, null, {name:prjname, key:key, newkey:document.getElementById("filter").value, code:document.getElementById("fix").textContent});
		}}).innerHTML = '<img src="assets/images/confirm.png">Confirm';
		addTo(fragment, "div", {cls:["interact"], onclick:function(){
			postAPI("/api/update_patch", browse_patches, null, {name:prjname, key:key});
		}}).innerHTML = '<img src="assets/images/trash.png">Delete';
		
		if(key != null)
		{
			fragment.getElementById("filter").value = key;
			fragment.getElementById("fix").textContent = prj["patches"][key];
		}
		updateMain(fragment);
	}
	catch(err)
	{
		console.error("Exception thrown", err.stack);
		pushPopup("An unexpected error occured.");
		project_menu();
	}
}

// open backup list
function backup_list(data)
{
	try
	{
		// top part
		let fragment = clearBar();
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			project_menu();
		}}).innerHTML = '<img src="assets/images/back.png">';
		addTo(fragment, "div", {cls:["inline"], br:false}).innerHTML = prjname;
		addTo(fragment, "div", {cls:["barfill"], br:false});
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			document.getElementById("help").innerHTML = "<ul>\
				<li>Select an existing backup to use it.</li>\
				<li>Click Twice of CTRL+Click on <b>Use</b> to select the backup.</li>\
				<li>Existing strings.json and its backups will be properly kept, while the selected backup will become the new strings.json.</li>\
			</ul>";
			document.getElementById("help").style.display = "";
		}}).innerHTML = '<img src="assets/images/help.png">';
		updateBar(fragment);
		
		// main part
		fragment = clearMain();
		addTo(fragment, "div", {cls:["title"]}).innerHTML = prjname;
		addTo(fragment, "div", {cls:["title", "left"]}).innerHTML = "Backup List";
		if(data["list"].length == 0)
			addTo(fragment, "div", {cls:["title", "left", "block", "inline"], br:false}).innerHTML = "No backup available";
		for(const elem of data["list"])
		{
			addTo(fragment, "div", {cls:["interact", "text-button", "inline"], br:false, onclick:function(){
				if(this.classList.contains("selected") || window.event.ctrlKey)
					postAPI("/api/load_backup", project_menu, null, {name:prjname, file:elem[0]});
				else
				{
					this.classList.add("selected");
					pushPopup("Press again to confirm.");
				}
			}}).innerHTML = '<img src="assets/images/copy.png">Use';
			addTo(fragment, "div", {cls:["title", "left", "block", "inline"], br:false}).innerHTML = elem[0];
			let size = "";
			if(elem[1] >= 1048576) size = Math.round(elem[1] / 1048576) + "MB";
			else if(elem[1] >= 1024) size = Math.round(elem[1] / 1024) + "KB";
			else size = elem[1] + "B";
			addTo(fragment, "div", {cls:["title", "left", "block", "inline", "smalltext"], br:false}).innerHTML = size;
			addTo(fragment, "div", {cls:["title", "left", "block", "inline", "smalltext"]}).innerHTML = new Date(elem[2]*1000).toISOString().split('.')[0].replace('T', ' ');
		}
		updateMain(fragment);
	}
	catch(err)
	{
		console.error("Exception thrown", err.stack);
		pushPopup("An unexpected error occured.");
		project_menu();
	}
}

// update file elements
function update_file_list(data)
{
	try
	{
		set_loading(false);
		for(const [key, value] of Object.entries(data["files"]))
		{
			if(value) document.getElementById("text:"+key).classList.add("disabled");
			else document.getElementById("text:"+key).classList.remove("disabled");
		}
	}
	catch(err)
	{
		console.error("Exception thrown", err.stack);
		pushPopup("An unexpected error occured.");
		project_menu();
	}
}

// Prepare string space for string list
function prepareGroupOn(node, i)
{
	let base = addTo(node, "div", {cls:["interact-group"]});
	let group = addTo(base, "span", {cls:["smalltext"], id:i});
	if(prjlist[i][0] != "")
		group.textContent = prjlist[i][0];
	else
		group.textContent = "#"+(i+1);
	for(let j = 1; j < prjlist[i].length; ++j)
	{
		const span = addTo(base, "span", {cls:["interact", "string-group"]});
		span.group = i;
		span.string = j;
		
		let marker = addTo(span, "div", {cls:["marker", "inline"], br:false});
		
		let original = addTo(span, "pre", {cls:["title", "inline", "smalltext", "original"], br:false});
		original.group = i;
		original.string = j;
		original.textContent = prjstring[prjlist[i][j][0]][0];
		
		let translation = addTo(span, "pre", {cls:["title", "inline", "smalltext", "translation"], br:false});
		translation.group = i;
		translation.string = j;
		
		strtablecache.push([span, marker, translation, original]);
		const tsize = strtablecache.length - 1;
		
		span.onclick = function()
		{
			if(window.event.ctrlKey && !window.event.shiftKey)
			{
				laststringinteracted = tsize;
				set_loading_text("Updating...");
				postAPI("/api/update_string", update_string_list, null, {setting:1, version:prjversion, name:prjname, path:prjdata["path"], group:this.group, index:this.string});
			}
			else if(!window.event.ctrlKey && window.event.shiftKey)
			{
				if(bottom.style.display == "none")
				{
					laststringinteracted = tsize;
					set_loading_text("Updating...");
					postAPI("/api/update_string", update_string_list, null, {setting:0, version:prjversion, name:prjname, path:prjdata["path"], group:this.group, index:this.string});
				}
			}
		};
		original.onclick = function()
		{
			if(!window.event.ctrlKey && !window.event.shiftKey && window.event.altKey)
			{
				if(navigator.clipboard != undefined)
				{
					laststringinteracted = tsize;
					navigator.clipboard.writeText(original.textContent);
					pushPopup('The String has been copied');
				}
				else pushPopup('You need to be on a secure origin to use the Copy button');
			}
		};
		translation.onclick = function()
		{
			if(!window.event.ctrlKey && !window.event.shiftKey)
			{
				if(window.event.altKey)
				{
					if(navigator.clipboard != undefined)
					{
						laststringinteracted = tsize;
						navigator.clipboard.writeText(translation.textContent);
						pushPopup('The String has been copied');
					}
					else pushPopup('You need to be on a secure origin to use the Copy button');
				}
				else
				{
					laststringinteracted = tsize;
					let ss = prjlist[span.group][span.string];
					document.getElementById("edit-ori").textContent = prjstring[ss[0]][0];
					let edittl = document.getElementById("edit-tl");
					if(ss[2])
					{
						if(ss[1] != null)
							edittl.value = ss[1];
						else
							edittl.value = prjstring[ss[0]][0]; // default to original
					}
					else if(prjstring[ss[0]][1] != null)
						edittl.value = prjstring[ss[0]][1];
					else
						edittl.value = prjstring[ss[0]][0]; // default to original
					document.getElementById("string-length").innerHTML = edittl.value.length;
					bottom.style.display = "";
					edittl.focus();
					currentstr = span;
				}
			}
		};
	}
}

// open a file content
function open_file(data)
{
	try
	{
		keypressenabled = true;
		laststringinteracted = 0;
		prjstring = data["strings"];
		prjlist = data["list"];
		prjdata = data;
		lastfileopened = data["path"];
		
		// top bar
		let fragment = clearBar();
		const returnpath = lastfileopened.includes('/') ? lastfileopened.split('/').slice(0, lastfileopened.split('/').length-1).join('/')+'/' : "";
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			bottom.style.display = "none";
			if(laststringsearch != null)
				postAPI("/api/search_string", string_search, null, {name:prjname, path:returnpath, search:laststringsearch});
			else
				postAPI("/api/browse", browse_files, null, {name:prjname, path:returnpath});
		}}).innerHTML = '<img src="assets/images/back.png">';
		addTo(fragment, "div", {cls:["inline"], br:false}).innerHTML = "File: " + lastfileopened;
		addTo(fragment, "div", {cls:["barfill"], br:false});
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			document.getElementById("help").innerHTML = "<ul>\
				<li>CTRL+Click on a line to <b>disable</b> it, it'll be skipped during the release process.</li>\
				<li>SHIFT+Click on a line to <b>unlink</b> it, if you need to set it to a translation specific to this part of the file.</li>\
				<li>ALT+Click on the original string (on the left) to copy it.</li>\
				<li>ALT+Click on the translated string (on the right) to copy it.</li>\
				<li>Click on the translated string (on the right) to edit it.</li>\
				<li>SHIFT+Space to scroll to the next untranslated string.</li>\
				<li>CTRL+Space to scroll to the next untranslated <b>enabled</b> string.</li>\
				<li>On top, if available, you'll find <b>Plugin Actions</b> for this file.</li>\
				<li>You'll also find the <b>Translate the File</b> button.</li>\
			</ul>";
			document.getElementById("help").style.display = "";
		}}).innerHTML = '<img src="assets/images/help.png">';
		updateBar(fragment);
		
		// main part
		fragment = clearMain();
		
		let topsection = addTo(fragment, "div", {cls:["title"]});
		topsection.innerHTML = prjname;
		addTo(fragment, "div", {cls:["title", "left"]}).innerHTML = lastfileopened;
		
		for(const [key, value] of Object.entries(data["actions"]))
		{
			addTo(fragment, "div", {cls:["interact"], onclick:function() {
				postAPI("/api/file_action", null, function() {
					postAPI("/api/browse", browse_files, null, {name:prjname, path:returnpath});
				}, {name:prjname, path:lastfileopened, version:prjversion, key:key});
			}}).innerHTML = '<img src="assets/images/setting.png">' + value;
		}
		addTo(fragment, "div", {cls:["interact"], onclick:function() {
			set_loading_text("Translating this file...")
			postAPI("/api/translate_file", update_string_list, function(){
				bottom.style.display = "none";
				postAPI("/api/browse", browse_files, null, {name:prjname, path:returnpath});
			}, {name:prjname, path:lastfileopened, version:prjversion});
		}}).innerHTML = '<img src="assets/images/translate.png">Translate the File';
		
		strtablecache = [];
		for(let i = 0; i < prjlist.length; ++i)
		{
			prepareGroupOn(fragment, i);
		}
		addTo(fragment, "div", {cls:["spacer"]});
		addTo(fragment, "div", {cls:["spacer"]});
		addTo(fragment, "div", {cls:["spacer"]});
		updateMain(fragment);
		let scrollTo = update_string_list(data);
		if(scrollTo)
			scrollTo.scrollIntoView();
		else
			topsection.scrollIntoView();
	}
	catch(err)
	{
		keypressenabled = false;
		console.error("Exception thrown", err.stack);
		pushPopup("An unexpected error occured.");
		bottom.style.display = "none";
		project_menu();
	}
}

function copy_string() // used on the index.html
{
	if(navigator.clipboard != undefined)
	{
		navigator.clipboard.writeText(document.getElementById('edit-ori').textContent);
		pushPopup('Original String has been copied');
	}
	else pushPopup('You need to be on a secure origin to use the Copy button');
}

// send and confirm a string change
function apply_string(trash = false)
{
	bottom.style.display = "none";
	set_loading_text("Updating...");
	const returnpath = prjdata["path"].includes('/') ? prjdata["path"].split('/').slice(0, prjdata["path"].split('/').length-1).join('/')+'/' : "";
	if(trash)
		postAPI("/api/update_string", update_string_list, function(){
			bottom.style.display = "none";
			postAPI("/api/browse", browse_files, null, {name:prjname, path:returnpath});
		}, {name:prjname, version:prjversion, path:prjdata["path"], group:currentstr.group, index:currentstr.string});
	else
		postAPI("/api/update_string", update_string_list, function(){
			bottom.style.display = "none";
			postAPI("/api/browse", browse_files, null, {name:prjname, path:returnpath});
		}, {name:prjname, version:prjversion, path:prjdata["path"], group:currentstr.group, index:currentstr.string, string:document.getElementById("edit-tl").value});
}

// update the string list
function update_string_list(data)
{
	let searched = null;
	try
	{
		set_loading_text("OK");
		prjstring = data["strings"];
		prjlist = data["list"];
		let updated = "updated" in data ? data["updated"] : null; // list of updated string
		let lcstringsearch = laststringsearch != null ? laststringsearch.toLowerCase() : "";
		for(let i = 0; i < strtablecache.length; ++i)
		{
			if(updated != null && !updated.includes(i)) // if null or in the updated list, we update
				continue; // else continue
			const elems = strtablecache[i];
			const s = prjlist[elems[0].group][elems[0].string];
			if(s[2]) // local/linked check
			{
				elems[0].classList.toggle("unlinked", true);
				if(s[1] == null)
				{
					if(elems[2].textContent != "")
						elems[2].textContent = "";
					elems[2].classList.toggle("disabled", true);
				}
				else
				{
					if(elems[2].textContent != s[1])
						elems[2].textContent = s[1];
					elems[2].classList.toggle("disabled", false);
				}
			}
			else // global
			{
				elems[0].classList.toggle("unlinked", false);
				const g = prjstring[s[0]];
				if(g[1] == null)
				{
					if(elems[2].textContent != "")
						elems[2].textContent = "";
					elems[2].classList.toggle("disabled", true);
				}
				else
				{
					if(elems[2].textContent != g[1])
						elems[2].textContent = g[1];
					elems[2].classList.toggle("disabled", false);
				}
			}
			elems[0].classList.toggle("disabled", s[3] != 0);
			elems[1].classList.toggle("modified", s[4] != 0);
			if(laststringsearch != null && searched == null && (elems[2].textContent.toLowerCase().includes(lcstringsearch) || elems[3].textContent.toLowerCase().includes(lcstringsearch)))
				searched = elems[2].parentNode;
		}
		set_loading(false);
	}
	catch(err)
	{
		console.error("Exception thrown", err.stack);
		pushPopup("An unexpected error occured.");
		project_menu();
	}
	return searched;
}

function translate_string()
{
	set_loading_text("Fetching translation...");
	postAPI("/api/translate_string", function(data) {
		set_loading(false);
		if(data["translation"] != null)
			document.getElementById("edit-tl").value = data["translation"];
	}, function() {}, {name:prjname, string:document.getElementById("edit-ori").textContent});
}