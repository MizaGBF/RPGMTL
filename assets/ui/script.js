// main parts
var bar = null;
var main = null;
var bottom = null;
var loader = null;
var loadertext = null;
var loaderanim = null;
var help = null;
var edit_ori = null;
var edit_tl = null;
var tl_string_length = null;
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
var filebrowsingmode = 0;

// entry point
function init()
{
	// register the main elements
	bar = document.getElementById("top");
	main = document.getElementById("main");
	bottom = document.getElementById("bottom");
	loader = document.getElementById("loading");
	loadertext = document.getElementById("loader-text");
	loaderanim = document.getElementById("loader-animation");
	help = document.getElementById("help");
	edit_ori = document.getElementById("edit-ori");
	edit_tl = document.getElementById("edit-tl");
	tl_string_length = document.getElementById("string-length");
	// request the project list
	postAPI("/api/main", project_list);
}

// for keyboard Space shortcut detection during file editing
document.onkeypress = function(e)
{
	if(keypressenabled) // flag to enable this function
	{
		if(e.code == 'Space' && strtablecache.length > 0 && e.target.tagName != "textarea") // check if space key was pressed and not on textarea
		{
			if(e.ctrlKey && !e.shiftKey) // CTRL+space
			{
				let i = (laststringinteracted + 1) % strtablecache.length; // iterate over cached strings until we find one without translation
				while(i != laststringinteracted)
				{
					if(!strtablecache[i][0].classList.contains("disabled") && strtablecache[i][2].classList.contains("disabled")) // this one also makes sure the string is enabled
					{
						laststringinteracted = i;
						strtablecache[i][0].scrollIntoView();
						break;
					}
					i = (i + 1) % strtablecache.length;
				}
				e.stopPropagation();
			}
			else if(e.ctrlKey && e.shiftKey) // CTRL+SHIFT+space
			{
				let i = (laststringinteracted + 1) % strtablecache.length;
				while(i != laststringinteracted)
				{
					if(strtablecache[i][2].classList.contains("disabled")) // same as above, without the enabled check
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
// support various parameters
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
		loaderanim.classList.add("loader");
		loader.style.display = null;
	}
	else
	{
		loaderanim.classList.remove("loader");
		loader.style.display = "none";
	}
}

// set the loading element text
function set_loading_text(content)
{
	loadertext.textContent = content;
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
	set_loading(true); // enable loading element
	var xhr = new XMLHttpRequest();
	// we call processAPI regardless of result, with our success/failure callbacks
	xhr.ontimeout = function () {
		processAPI.apply(xhr, [success, failure]);
	};
	xhr.onload = function() {
		if (xhr.readyState === 4) {
			processAPI.apply(xhr, [success, failure]);
		}
	};
	xhr.open(type, url, true); // set request type here
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

// display a popup with the given string for 4s
function pushPopup(string)
{
	let div = document.createElement('div');
	div.className = 'popup';
	div.innerHTML = string;
	document.body.appendChild(div);
	setTimeout(rmPopup, 4000, div);
}

// remove a popup
function rmPopup(popup)
{
	popup.parentNode.removeChild(popup);
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
		if(json["result"] == "ok") // good result
		{
			if("name" in json["data"] && "config" in json["data"]) // check data content (note: data MUST be present)
			{
				// keep project infos up to date
				prjname = json["data"]["name"];
				prj = json["data"]["config"];
				prjversion = prj["version"];
			}
			if(success) // call success callback if it exists
				success(json["data"]);
			else
				set_loading(false);
		}
		else
		{
			if(failure) // call failure callback if it exists
				failure(json);
			else
				set_loading(false);
		}
		// reset loading text
		set_loading_text("Waiting RPGMTL response...");
	}
	catch(err)
	{
		console.error("Exception thrown", err.stack);
		set_loading_text("An unexpected error occured.<br>" + err.stack + "<br><br>Refresh the page.<br>Make sure to report the bug if the issue continue.");
	}
}

// handle result of /api/main
function project_list(data)
{
	// Reset major variables
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
	// shutdown button
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
	// add version
	addTo(fragment, "div", {cls:["inline"], br:false}).innerHTML = 'RPGMTL v' + data["verstring"];
	addTo(fragment, "div", {cls:["barfill"], br:false});
	// github
	addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
		window.open("https://github.com/MizaGBF/RPGMTL", "_blank")
	}}).innerHTML = '<img src="assets/images/github.png">';
	// help
	addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
		help.innerHTML = "<ul>\
			<li>Load an existing <b>Project</b> or create a new one.</li>\
			<li>Click twice on the Shutdown button to stop RPGMTL remotely.</li>\
		</ul>";
		help.style.display = "";
	}}).innerHTML = '<img src="assets/images/help.png">';
	updateBar(fragment);
	
	// main part
	fragment = clearMain();
	addTo(fragment, "div", {cls:["title"]}).innerHTML = "Project List";
	if(data["list"].length > 0) // list projects
	{
		for(let i = 0; i < data["list"].length; ++i)
		{
			const t = data["list"][i];
			addTo(fragment, "div", {cls:["interact"], onclick:function(){
				postAPI("/api/open_project", project_menu, project_fail, {"name":t});
			}}).innerHTML = data["list"][i];
		}
	}
	addTo(fragment, "div", {cls:["spacer"]});
	// add buttons
	addTo(fragment, "div", {cls:["interact"], onclick:function(){
		local_browse("Create a project", "Select a Game executable.", 0);
	}}).innerHTML = '<img src="assets/images/new.png">New Project';
	addTo(fragment, "div", {cls:["interact"], onclick:function(){
		postAPI("/api/settings", setting_menu);
	}}).innerHTML = '<img src="assets/images/setting.png">Global Settings';
	addTo(fragment, "div", {cls:["interact"], onclick:function(){
		postAPI("/api/translator", translator_menu);
	}}).innerHTML = '<img src="assets/images/translate.png">Default Translator';
	updateMain(fragment);
}

// display settings for /api/settings
function setting_menu(data)
{
	try
	{
		const is_project = "config" in data;
		// top bar
		let fragment = clearBar();
		// back button
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			if(is_project)
				project_menu();
			else
				postAPI("/api/main", project_list);
		}}).innerHTML = '<img src="assets/images/back.png">';
		// add project name or default string
		addTo(fragment, "div", {cls:["inline"], br:false}).innerHTML = is_project ? prjname + " Settings" : "Default Settings";
		addTo(fragment, "div", {cls:["barfill"], br:false});
		// help button
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			help.innerHTML = "<ul>\
				<li>Some settings might require you to extract your project strings again, be careful to not lose progress.</li>\
				<li><b>Default</b> Settings are your projects defaults.</li>\
				<li><b>Project</b> Settings override <b>Default</b> Settings when modified.</li>\
			</ul>";
			help.style.display = "";
		}}).innerHTML = '<img src="assets/images/help.png">';
		updateBar(fragment);
		
		// main part
		fragment = clearMain();
		let layout = data["layout"];
		let settings = data["settings"];
		
		if(is_project) // add button to reset settings of THIS project
		{
			addTo(fragment, "div", {cls:["interact"], onclick:function(){
				postAPI("/api/update_settings", function(result_data) {
					pushPopup("The Project Settings have been reset to Global Settings.");
					project_menu();
				}, null, {name:prjname});
			}}).innerHTML = '<img src="assets/images/trash.png">Reset All Settings to Global';
		}
		
		let count = 0;
		// go over received setting menu layout
		for(const [file, fsett] of Object.entries(layout))
		{
			// add plugin name
			addTo(fragment, "div", {cls:["title", "left"], br:false}).innerHTML = file + " Plugin settings";
			// and description if it exists
			if(file in data["descriptions"] && data["descriptions"][file] != "")
				addTo(fragment, "div", {cls:["left", "interact-group", "smalltext"]}).innerText = data["descriptions"][file];
			// go over options
			for(const [key, fdata] of Object.entries(fsett))
			{
				switch(fdata[1])
				{
					case "bool": // bool type
					{
						addTo(fragment, "div", {cls:["settingtext"], br:false}).innerHTML = fdata[0];
						// add a simple toggle
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
							// add an input element
							const input = addTo(fragment, "input", {cls:["input", "smallinput"], br:false});
							input.type = "text";
							// and confirmation button
							const elem = addTo(fragment, "div", {cls:["interact", "button"], onclick:function(){
								let val = "";
								switch(fdata[1]) // make sure our value is what RPGMTL wants
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
							// add listener to detect keypress
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
							// add select and option elements
							const sel = addTo(fragment, "select", {cls:["input", "smallinput"], br:false});
							for(let i = 0; i < fdata[2].length; ++i)
							{
								let opt = addTo(sel, "option");
								opt.value = fdata[2][i];
								opt.textContent = fdata[2][i];
							}
							// and confirmation button
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

// translator pick menu /api/translator
function translator_menu(data)
{
	try
	{
		const is_project = "config" in data;
		// top bar
		let fragment = clearBar();
		// back button
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			if(is_project)
				project_menu();
			else
				postAPI("/api/main", project_list);
		}}).innerHTML = '<img src="assets/images/back.png">';
		// project name or default string
		addTo(fragment, "div", {cls:["inline"], br:false}).innerHTML = is_project ? prjname + " Settings" : "Global Settings";
		addTo(fragment, "div", {cls:["barfill"], br:false});
		// help button
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			help.innerHTML = "<ul>\
				<li>Select the Translator Plugin to use.</li>\
				<li><b>Default</b> Translator is used by default.</li>\
				<li><b>Project</b> Translator override the <b>Default</b> when modified.</li>\
			</ul>";
			help.style.display = "";
		}}).innerHTML = '<img src="assets/images/help.png">';
		updateBar(fragment);
		
		// main part
		fragment = clearMain();
		let list = data["list"]; // translator plugin list
		let current = data["current"];
		if(list.length == 0)
		{
			addTo(fragment, "div", {cls:["title", "left"]}).innerHTML = "No Translator Plugin available";
		}
		else
		{
			if(is_project) // add button to reset project setting
			{
				addTo(fragment, "div", {cls:["interact"], onclick:function(){
					postAPI("/api/update_translator", function(result_data) {
						pushPopup("The Project Translator have been reset to the default.");
						project_menu();
					}, null, {name:prjname});
				}}).innerHTML = '<img src="assets/images/trash.png">Use RPGMTL Default';
			}
			
			// add select and option elements
			const sel = addTo(fragment, "select", {cls:["input", "smallinput"], br:false});
			for(let i = 0; i < list.length; ++i)
			{
				let opt = addTo(sel, "option");
				opt.value = list[i];
				opt.textContent = list[i];
			}
			// and confirmation button
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

// project creation /api/update_location
function project_creation(data)
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
		// back button
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			postAPI("/api/main", project_list);
		}}).innerHTML = '<img src="assets/images/back.png">';
		// set page title
		addTo(fragment, "div", {cls:["inline"], br:false}).innerHTML = 'Create a new Project';
		addTo(fragment, "div", {cls:["barfill"], br:false});
		// help button
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			help.innerHTML = "<ul>\
				<li>The Project Name has little importance, just make sure you know what it refers to.</li>\
				<li>If already taken, a number will be added after the name.</li>\
			</ul>";
			help.style.display = "";
		}}).innerHTML = '<img src="assets/images/help.png">';
		updateBar(fragment);
		
		// main part
		fragment = clearMain();
		addTo(fragment, "div", {cls:["title", "left"]}).innerHTML = "Folder/Project Name";
		
		// project name input element
		let input = addTo(fragment, "input", {cls:["input"]});
		input.type = "text";
		
		let tmp = path.split("/"); // set input default value
		if(tmp.length >= 1)
			input.value = tmp[tmp.length-1];
		else
			input.value = "Project";
		
		// confirm button
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

// display project options (called by many API and more, data is optional and unused)
function project_menu(data = null)
{
	try
	{
		// top bar
		let fragment = clearBar();
		// back button
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			postAPI("/api/main", project_list);
		}}).innerHTML = '<img src="assets/images/back.png">';
		addTo(fragment, "div", {cls:["inline"], br:false}).innerHTML = prjname;
		addTo(fragment, "div", {cls:["barfill"], br:false});
		// help button
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			help.innerHTML = "<ul>\
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
				<li><b>Import RPGMTL</b> to import strings from RPGMTL projects from any version.</li>\
				<li><b>Strings Backups</b> to open the list of backups if you need to revert the project data to an earlier state.</li>\
			</ul>";
			help.style.display = "";
		}}).innerHTML = '<img src="assets/images/help.png">';
		updateBar(fragment);
		
		// main part
		// here we add various buttons
		// some only appear if files have been parsed
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
			local_browse("Update project files", "Select the Game executable.", 1);
		}}).innerHTML = '<img src="assets/images/update.png">Update the Game Files';
		addTo(fragment, "div", {cls:["interact"], onclick:function(){
			set_loading_text("Extracting, be patient...");
			postAPI("/api/extract", project_menu, project_fail, {name:prjname});
		}}).innerHTML = '<img src="assets/images/export.png">Extract the Strings';
		if(prj.files)
		{
			addTo(fragment, "div", {cls:["interact"], onclick:function(){
				set_loading_text("The patch is being generated in the release folder...");
				postAPI("/api/release", project_menu, null, {name:prjname});
			}}).innerHTML = '<img src="assets/images/release.png">Release a Patch';
			addTo(fragment, "div", {cls:["spacer"]});
			addTo(fragment, "div", {cls:["interact"], onclick:function(){
				postAPI("/api/backups", backup_list, null, {name:prjname});
			}}).innerHTML = '<img src="assets/images/copy.png">String Backups';
			addTo(fragment, "div", {cls:["interact"], onclick:function(){
				local_browse("Import RPGMTL", "Select an old RPGMTL strings file.", 2);
			}}).innerHTML = '<img src="assets/images/import.png">Import Strings from RPGMTL v1/v2';
			addTo(fragment, "div", {cls:["interact"], onclick:function(){
				local_browse("Import RPGMAKERTRANSPATCH", "Select a RPGMAKERTRANSPATCH file.", 3);
			}}).innerHTML = '<img src="assets/images/import.png">Import Strings from RPGMakerTrans v3';
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

// generic function to add a search bar on top of the browse file page
function addSearchBar(node, bp, defaultVal = null)
{
	// input element
	const input = addTo(node, "input", {cls:["input", "smallinput"], br:false});
	input.placeholder = "Search a string";
	if(defaultVal != null)
		input.value = defaultVal;
	else if(laststringsearch != null) // set last string searched if not null
		input.value = laststringsearch;
	else
		input.value = "";
	// add confirm button
	const button = addTo(node, "div", {cls:["interact", "button"], onclick:function(){
		if(input.value != "")
		{
			laststringsearch = input.value;
			postAPI("/api/search_string", string_search, null, {name:prjname, path:bp, search:laststringsearch});
		}
	}});
	button.innerHTML = '<img src="assets/images/search.png">';
	// and listener for return key
	input.addEventListener('keypress', function(event) {
		if (event.key === 'Enter')
		{
			event.preventDefault();
			button.click();
		}
	});
}

// search original button, used in index.html
function search_this()
{
	bottom.style.display = "none";
	postAPI("/api/search_string", string_search, null, {name:prjname, path:prjdata["path"], search:document.getElementById('edit-ori').textContent});
}

// open folder /api/browse
function browse_files(data)
{
	try
	{
		keypressenabled = false;
		laststringsearch = null;
		const bp = data["path"];
		// top bar
		let fragment = clearBar();
		// back button
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function() {
			let returnpath = bp.includes('/') ? bp.split('/').slice(0, bp.split('/').length-2).join('/')+'/' : "";
			// returnpath is the path of the parent folder
			if(bp == "") // current folder is the root, so back to menu
				project_menu();
			else
			{
				if(returnpath == '/') returnpath = ''; // if return path is a single slash, set to empty first
				postAPI("/api/browse", browse_files, null, {name:prjname, path:returnpath});
			}
		}}).innerHTML = '<img src="assets/images/back.png">';
		addTo(fragment, "div", {cls:["inline"], br:false}).innerHTML = "Path: " + bp;
		addTo(fragment, "div", {cls:["barfill"], br:false});
		// help button
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			help.innerHTML = "<ul>\
				<li>CTRL+Click on a file to <b>disable</b> it, it won't be patched during the release process.</li>\
				<li>The string counts and completion percentages update slowly in the background, don't take them for granted.</li>\
			</ul>";
			help.style.display = "";
		}}).innerHTML = '<img src="assets/images/help.png">';
		updateBar(fragment);
		
		// main part
		fragment = clearMain();
		addTo(fragment, "div", {cls:["title"]}).innerHTML = prjname;
		// add the string search
		addSearchBar(fragment, bp);
		
		// add completion indicator (filled at the bottom)
		let completion = addTo(fragment, "div", {cls:["title", "left"]});
		let fstring = 0;
		let ftotal = 0;
		let fcount = 0;
		
		addTo(fragment, "div", {cls:["title", "left"]}).innerHTML = bp;
		// go over folders
		for(let i = 0; i < data["folders"].length; ++i)
		{
			const t = data["folders"][i];
			let div = addTo(fragment, "div", {cls:["interact"]});
			if(t == "..") // special one indicating we aren't on the root level
			{
				div.innerHTML = '<img src="assets/images/back.png">..';
			}
			else if(prj["files"][t.slice(0, -1)] != undefined) // for archive type files
			{
				div.innerHTML = '<img src="assets/images/archive.png">' + t;
			}
			else
			{
				div.innerHTML = '<img src="assets/images/folder.png">' + t;
			}
			div.onclick = function() // add callback
			{
				if(t == "..") // used for the "parent folder" button
				{
					let s = bp.split("/"); // at least 2 elements in s means there is one slash in the path, i.e. we aren't in the root level
					if(s.length == 2)
						postAPI("/api/browse", browse_files, null, {name:prjname, path:""});
					else
						postAPI("/api/browse", browse_files, null, {name:prjname, path:s.slice(0, s.length-2).join("/") + "/"});
				}
				else // open whatever folder it is
					postAPI("/api/browse", browse_files, null, {name:prjname, path:t});
			};
		}
		addTo(fragment, "div", {cls:["title", "left"]}).innerHTML = "List of Files";
		// possible class sets
		let cls = [
			["interact"],
			["interact", "disabled"]
		];
		let scrollTo = null; // contains element to scroll to
		for(const [key, value] of Object.entries(data["files"]))
		{
			// add button
			let button = addTo(fragment, "div", {cls:cls[+value], br:false, id:"text:"+key, onclick:function(){
				if(window.event.ctrlKey) // ignore shortcut
				{
					postAPI("/api/ignore_file", update_file_list, null, {name:prjname, path:key, state:+!this.classList.contains("disabled")});
				}
				else
				{
					set_loading_text("Opening " + key + "...");
					postAPI("/api/file", open_file, null, {name:prjname, path:key});
				}
			}});
			// add completion indicator
			let total = prj["files"][key]["strings"] - prj["files"][key]["disabled_strings"];
			let count = prj["files"][key]["translated"];
			let percent = total > 0 ? ", " + (Math.round(10000 * count / total) / 100) + "%)" : ")";
			
			if(!value) // add to folder completion indicator
			{
				fstring += prj["files"][key]["strings"];
				ftotal += total;
				fcount += count;
			}
			
			if(count == total) // add complete class if no string left to translate
				button.classList.add("complete");
			button.textContent = key + ' (' + prj["files"][key]["strings"] + percent; // set text
			if(key == lastfileopened) // if this is the last opened file
				scrollTo = button; // store it
		}
		addTo(fragment, "div", {cls:["spacer"]});
		addTo(fragment, "div", {cls:["spacer"]});
		addTo(fragment, "div", {cls:["spacer"]});
		// set folder completion indicator
		let percent = ftotal > 0 ? ', ' + (Math.round(10000 * fcount / ftotal) / 100) + '%' : '';
		completion.textContent = "Current Total: " + fstring + " strings" + percent;
		updateMain(fragment);
		if(scrollTo != null) // scroll to last opened file
			scrollTo.scrollIntoView();
		lastfileopened = null; // and clear it
	}
	catch(err)
	{
		lastfileopened = null;
		console.error("Exception thrown", err.stack);
		pushPopup("An unexpected error occured.");
		project_menu();
	}
}

// search a string /api/search_string
// it copy/paste stuff from the browse function
function string_search(data)
{
	try
	{
		const bp = data["path"];
		// top bar
		let fragment = clearBar();
		// back button (return to browse_files)
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function() {
			postAPI("/api/browse", browse_files, null, {name:prjname, path:data["path"]});
		}}).innerHTML = '<img src="assets/images/back.png">';
		addTo(fragment, "div", {cls:["inline"], br:false}).innerHTML = "Search Results";
		addTo(fragment, "div", {cls:["barfill"], br:false});
		// help menu
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			help.innerHTML = "<ul>\
				<li>Your search results are displayed here.</li>\
			</ul>";
			help.style.display = "";
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
		// list files
		for(const [key, value] of Object.entries(data["files"]))
		{
			let button = addTo(fragment, "div", {cls:cls[+value], br:false, id:"text:"+key, onclick:function(){
				if(window.event.ctrlKey) // disable shortcut
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
		// back button
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			project_menu();
		}}).innerHTML = '<img src="assets/images/back.png">';
		addTo(fragment, "div", {cls:["inline"], br:false}).innerHTML = prjname;
		addTo(fragment, "div", {cls:["barfill"], br:false});
		// help button
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			help.innerHTML = "<ul>\
				<li>Select an existing patch/fix or create a new one.</li>\
				<li>The patch/fix will be applied on all files whose name contains the patch/fix name.</li>\
				<li>The patch/fix code must be valid <b>Python</b> code, refer to the <b>README</b> for details.</li>\
			</ul>";
			help.style.display = "";
		}}).innerHTML = '<img src="assets/images/help.png">';
		updateBar(fragment);
		
		// main part
		fragment = clearMain();
		addTo(fragment, "div", {cls:["title"]}).innerHTML = prjname;
		addTo(fragment, "div", {cls:["title", "left"]}).innerHTML = "Fix List";
		// list patches
		for(const [key, value] of Object.entries(prj["patches"]))
		{
			// add button to open
			addTo(fragment, "div", {cls:["interact"], onclick:function()
			{
				postAPI("/api/open_patch", edit_patch, null, {name:prjname, key:key});
			}
			}).innerHTML = '<img src="assets/images/bandaid.png">' + key;
		}
		addTo(fragment, "div", {cls:["spacer"]});
		// add create button
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

// edit a fix /api/open_patch
function edit_patch(data)
{
	try
	{
		const key = data["key"]; // patch key. Note: CAN be null
		// top bar
		let fragment = clearBar();
		// back button
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			postAPI("/api/patches", browse_patches, null, {name:prjname});
		}}).innerHTML = '<img src="assets/images/back.png">';
		addTo(fragment, "div", {cls:["inline"], br:false}).innerHTML = "Create a Fix";
		addTo(fragment, "div", {cls:["barfill"], br:false});
		// help button
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			help.innerHTML = "<ul>\
				<li>Select an existing patch/fix or create a new one.</li>\
				<li>The patch/fix will be applied on all files whose name contains the patch/fix name.</li>\
				<li>The patch/fix code must be valid <b>Python</b> code, refer to the <b>README</b> for details.</li>\
			</ul>";
			help.style.display = "";
		}}).innerHTML = '<img src="assets/images/help.png">';
		updateBar(fragment);
		
		// main part
		fragment = clearMain();
		// add various input and text elements
		addTo(fragment, "div", {cls:["title"]}).innerHTML = prjname;
		addTo(fragment, "div", {cls:["title", "left"]}).innerHTML = "Filename match";
		addTo(fragment, "input", {cls:["input"], id:"filter"}).type = "text";
		addTo(fragment, "div", {cls:["title", "left"]}).innerHTML = "Fix Code";
		addTo(fragment, "div", {cls:["input"], id:"fix"}).contentEditable = "plaintext-only";
		// add confirm button
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

// open backup list /api/backups
function backup_list(data)
{
	try
	{
		// top part
		let fragment = clearBar();
		// back button
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			project_menu();
		}}).innerHTML = '<img src="assets/images/back.png">';
		addTo(fragment, "div", {cls:["inline"], br:false}).innerHTML = prjname;
		addTo(fragment, "div", {cls:["barfill"], br:false});
		// help button
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			help.innerHTML = "<ul>\
				<li>Select an existing backup to use it.</li>\
				<li>Click Twice or CTRL+Click on <b>Use</b> to select the backup.</li>\
				<li>Existing strings.json and its backups will be properly kept, while the selected backup will become the new strings.json.</li>\
			</ul>";
			help.style.display = "";
		}}).innerHTML = '<img src="assets/images/help.png">';
		updateBar(fragment);
		
		// main part
		fragment = clearMain();
		addTo(fragment, "div", {cls:["title"]}).innerHTML = prjname;
		addTo(fragment, "div", {cls:["title", "left"]}).innerHTML = "Backup List";
		if(data["list"].length == 0)
			addTo(fragment, "div", {cls:["title", "left", "block", "inline"], br:false}).innerHTML = "No backup available";
		// list project backups
		for(const elem of data["list"])
		{
			// add button to load it
			addTo(fragment, "div", {cls:["interact", "text-button", "inline"], br:false, onclick:function(){
				if(this.classList.contains("selected") || window.event.ctrlKey) // confirmation / shortcut to insta confirm
					postAPI("/api/load_backup", project_menu, null, {name:prjname, file:elem[0]});
				else
				{
					this.classList.add("selected");
					pushPopup("Press again to confirm.");
				}
			}}).innerHTML = '<img src="assets/images/copy.png">Use';
			addTo(fragment, "div", {cls:["title", "left", "block", "inline"], br:false}).innerHTML = elem[0];
			// add backup infos
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

// update file elements /api/ignore_file
function update_file_list(data)
{
	try
	{
		set_loading(false);
		for(const [key, value] of Object.entries(data["files"])) // simply update disabled class
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
	let base = addTo(node, "div", {cls:["interact-group"]}); // base container
	let group = addTo(base, "span", {cls:["smalltext"], id:i}); // group container
	if(prjlist[i][0] != "") // add group name OR index
		group.textContent = prjlist[i][0];
	else
		group.textContent = "#"+(i+1);
	// iterate over strings of this group
	for(let j = 1; j < prjlist[i].length; ++j)
	{
		const span = addTo(base, "span", {cls:["interact", "string-group"]}); // add container
		span.group = i;
		span.string = j;
		
		let marker = addTo(span, "div", {cls:["marker", "inline"], br:false}); // left marker (modified, plugins...)
		
		let original = addTo(span, "pre", {cls:["title", "inline", "smalltext", "original"], br:false}); // original string
		original.group = i;
		original.string = j;
		original.textContent = prjstring[prjlist[i][j][0]][0];
		
		let translation = addTo(span, "pre", {cls:["title", "inline", "smalltext", "translation"], br:false}); // translated string
		translation.group = i;
		translation.string = j;
		
		strtablecache.push([span, marker, translation, original]); // add to strtablecache
		const tsize = strtablecache.length - 1;
		// note: laststringinteracted is set to tsize (i.e. string index in table) whether a string is interacted with
		span.onclick = function() // add string interactions
		{
			if(window.event.ctrlKey && !window.event.shiftKey && !window.event.altKey) // single disable
			{
				laststringinteracted = tsize;
				set_loading_text("Updating...");
				postAPI("/api/update_string", update_string_list, null, {setting:1, version:prjversion, name:prjname, path:prjdata["path"], group:this.group, index:this.string});
			}
			else if(window.event.ctrlKey && !window.event.shiftKey && window.event.altKey) // multi disable
			{
				laststringinteracted = tsize;
				set_loading_text("Updating...");
				postAPI("/api/update_string", update_string_list, null, {setting:2, version:prjversion, name:prjname, path:prjdata["path"], group:this.group, index:this.string});
			}
			else if(!window.event.ctrlKey && window.event.shiftKey && !window.event.altKey) // unlink
			{
				if(bottom.style.display == "none")
				{
					laststringinteracted = tsize;
					set_loading_text("Updating...");
					postAPI("/api/update_string", update_string_list, null, {setting:0, version:prjversion, name:prjname, path:prjdata["path"], group:this.group, index:this.string});
				}
			}
		};
		original.onclick = function() // add original string copy
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
		translation.onclick = function() // add translated string copy AND open
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
					// string from project data
					let ss = prjlist[span.group][span.string];
					// update bottom part
					// set original string text
					edit_ori.textContent = prjstring[ss[0]][0];
					let edittl = edit_tl;
					// set textarea with current translation
					if(ss[2]) // local/unlinked
					{
						if(ss[1] != null)
							edittl.value = ss[1];
						else
							edittl.value = prjstring[ss[0]][0]; // default to original if not translated
					}
					else if(prjstring[ss[0]][1] != null) // global
						edittl.value = prjstring[ss[0]][1];
					else
						edittl.value = prjstring[ss[0]][0]; // default to original if not translated
					// update string-length indicator
					tl_string_length.innerHTML = edittl.value.length;
					// make element visible
					bottom.style.display = "";
					// focus
					edittl.focus();
					// set this span element as the current string being edited
					currentstr = span;
				}
			}
		};
	}
}

// open a file content /api/file
function open_file(data)
{
	try
	{
		// init stuff
		keypressenabled = true;
		laststringinteracted = 0;
		prjstring = data["strings"];
		prjlist = data["list"];
		prjdata = data;
		lastfileopened = data["path"];
		
		// top bar
		let fragment = clearBar();
		// folder path
		const returnpath = lastfileopened.includes('/') ? lastfileopened.split('/').slice(0, lastfileopened.split('/').length-1).join('/')+'/' : "";
		// back button
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			bottom.style.display = "none";
			if(laststringsearch != null) // return to search result if we came from here
				postAPI("/api/search_string", string_search, null, {name:prjname, path:returnpath, search:laststringsearch});
			else
				postAPI("/api/browse", browse_files, null, {name:prjname, path:returnpath});
		}}).innerHTML = '<img src="assets/images/back.png">';
		addTo(fragment, "div", {cls:["inline"], br:false}).innerHTML = "File: " + lastfileopened;
		addTo(fragment, "div", {cls:["barfill"], br:false});
		// help button
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			help.innerHTML = "<ul>\
				<li>CTRL+Click on a line to <b>disable</b> it, it'll be skipped during the release process.</li>\
				<li>ALT+CTRL+Click on a line to <b>disable</b> <b>ALL</b> this string occurence in this file.</li>\
				<li>SHIFT+Click on a line to <b>unlink</b> it, if you need to set it to a translation specific to this part of the file.</li>\
				<li>ALT+Click on the original string (on the left) to copy it.</li>\
				<li>ALT+Click on the translated string (on the right) to copy it.</li>\
				<li>Click on the translated string (on the right) to edit it.</li>\
				<li>CTRL+Space to scroll to the next untranslated <b>enabled</b> string.</li>\
				<li>SHIFT+CTRL+Space to scroll to the next untranslated string.</li>\
				<li>On top, if available, you'll find <b>Plugin Actions</b> for this file.</li>\
				<li>You'll also find the <b>Translate the File</b> button.</li>\
			</ul>";
			help.style.display = "";
		}}).innerHTML = '<img src="assets/images/help.png">';
		updateBar(fragment);
		
		// main part
		fragment = clearMain();
		
		let topsection = addTo(fragment, "div", {cls:["title"]});
		topsection.innerHTML = prjname;
		addTo(fragment, "div", {cls:["title", "left"]}).innerHTML = lastfileopened;
		
		// list file actions
		for(const [key, value] of Object.entries(data["actions"]))
		{
			addTo(fragment, "div", {cls:["interact"], onclick:function() {
				postAPI("/api/file_action", null, function() {
					postAPI("/api/browse", browse_files, null, {name:prjname, path:returnpath});
				}, {name:prjname, path:lastfileopened, version:prjversion, key:key});
			}}).innerHTML = '<img src="assets/images/setting.png">' + value;
		}
		// add translate this file button
		addTo(fragment, "div", {cls:["interact"], onclick:function() {
			if(this.classList.contains("selected") || window.event.ctrlKey) // confirmation / shortcut to insta confirm
			{
				set_loading_text("Translating this file...")
				postAPI("/api/translate_file", update_string_list, function(){
					bottom.style.display = "none";
					postAPI("/api/browse", browse_files, null, {name:prjname, path:returnpath});
				}, {name:prjname, path:lastfileopened, version:prjversion});
			}
			else
			{
				this.classList.add("selected");
				pushPopup("Press again to confirm.");
			}
		}}).innerHTML = '<img src="assets/images/translate.png">Translate the File';
		
		switch(prj["files"][lastfileopened]["file_type"])
		{
			case 0: // NORMAL
				break;
			case 1: // ARCHIVE
				addTo(fragment, "div", {cls:["interact"], onclick:function() {
					postAPI("/api/browse", browse_files, null, {name:prjname, path:lastfileopened + "/"});
				}}).innerHTML = '<img src="assets/images/archive.png">Access Files contained inside';
				break;
			case 2: // VIRTUAL
				addTo(fragment, "div", {cls:["interact"], onclick:function() {
					postAPI("/api/file", open_file, null, {name:prjname, path:prj["files"][lastfileopened]["parent"]});
				}}).innerHTML = '<img src="assets/images/archive.png">Open Parent File';
				break;
			case 3: // VIRTUAL_UNDEFINED
				break;
			default:
				break;
		};
		
		// list strings
		strtablecache = [];
		for(let i = 0; i < prjlist.length; ++i)
		{
			prepareGroupOn(fragment, i);
		}
		addTo(fragment, "div", {cls:["spacer"]});
		addTo(fragment, "div", {cls:["spacer"]});
		addTo(fragment, "div", {cls:["spacer"]});
		updateMain(fragment);
		// update the string list with the data
		let scrollTo = update_string_list(data);
		// scroll to string (if set)
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

function copy_string() // used in index.html
{
	if(navigator.clipboard != undefined)
	{
		navigator.clipboard.writeText(edit_ori.textContent);
		pushPopup('Original String has been copied');
	}
	else pushPopup('You need to be on a secure origin to use the Copy button');
}

// send and confirm a string change, used in index.html
// trash = whether the trash button got used instead
function apply_string(trash = false)
{
	bottom.style.display = "none";
	set_loading_text("Updating...");
	// folder path of file
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
		}, {name:prjname, version:prjversion, path:prjdata["path"], group:currentstr.group, index:currentstr.string, string:edit_tl.value});
}

// update the string list
function update_string_list(data)
{
	let searched = null;
	try
	{
		// update list in memory with received data
		prjstring = data["strings"];
		prjlist = data["list"];
		let updated = "updated" in data ? data["updated"] : null; // list of updated strings (if provided)
		let lcstringsearch = laststringsearch != null ? laststringsearch.toLowerCase() : ""; // last searched string (lowercase)
		// iterate over ALL strings
		for(let i = 0; i < strtablecache.length; ++i)
		{
			if(updated != null && !updated.includes(i)) // if present in the updated string list OR if no updated strings provided, we update
				continue; // else continue
			const elems = strtablecache[i];
			// retrieve string details
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
			// check if string is the target of a string search
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
	// return searched, which contains either null OR a string to scroll to
	return searched;
}

// used in index.html
function translate_string()
{
	set_loading_text("Fetching translation...");
	postAPI("/api/translate_string", function(data) {
		set_loading(false);
		if(data["translation"] != null)
		{
			edit_tl.value = data["translation"];
			tl_string_length.innerHTML = edittl.value.length;
		}
	}, function() {}, {name:prjname, string:edit_ori.textContent});
}

// base for file browsing via /api/local_path
function local_browse(title, explanation, mode)
{
	try
	{
		filebrowsingmode = mode;
		
		// top bar
		let fragment = clearBar();
		// back button
		addTo(fragment, "div", {cls:["interact", "button"], br:false, onclick:function(){
			switch(filebrowsingmode)
			{
				case 0:
					postAPI("/api/main", project_list);
					break;
				case 1:
				case 2:
				case 3:
					project_menu();
					break;
				default:
					// TODO
					break;
			}
		}}).innerHTML = '<img src="assets/images/back.png">';
		addTo(fragment, "div", {cls:["inline"], br:false}).innerHTML = title;
		addTo(fragment, "div", {cls:["barfill"], br:false});
		updateBar(fragment);
	
		// main part
		fragment = clearMain();
		addTo(fragment, "div", {cls:["title"]}).innerHTML = explanation;
		addTo(fragment, "div", {cls:["title"], id:"current_path"});
		addTo(fragment, "div", {cls:["left", "title"]}).innerHTML = "Folders";
		addTo(fragment, "div", {id:"folder_container"});
		addTo(fragment, "div", {cls:["left", "title"]}).innerHTML = "Files";
		addTo(fragment, "div", {id:"file_container"});
		updateMain(fragment);
		postAPI("/api/local_path", update_local_browse, null, {"path":"", "mode":filebrowsingmode});
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

function update_local_browse(data)
{
	document.getElementById("current_path").innerText = data["path"];
	let container = document.getElementById("folder_container");
	container.innerHTML = "";
	for(let i = 0; i < data["folders"].length; ++i)
	{
		const t = data["folders"][i];
		addTo(container, "div", {cls:["interact"], onclick:function(){
			if(t == "..")
			{
				if(data["path"].length == 3 && data["path"].endsWith(":/"))
				{
					// special windows case
					postAPI("/api/local_path", update_local_browse, null, {"path":"::", "mode":filebrowsingmode});
				}
				else
				{
					// parent directory
					postAPI("/api/local_path", update_local_browse, null, {"path":data["path"].split('/').slice(0, data["path"].split('/').length-1).join('/'), "mode":filebrowsingmode});
				}
			}
			else
			{
				postAPI("/api/local_path", update_local_browse, null, {"path":t, "mode":filebrowsingmode});
			}
		}}).innerHTML = t.split("/")[t.split("/").length-1];
	}
	
	container = document.getElementById("file_container");
	container.innerHTML = "";
	for(let i = 0; i < data["files"].length; ++i)
	{
		const t = data["files"][i];
		addTo(container, "div", {cls:["interact"], onclick:function(){
			switch(filebrowsingmode)
			{
				case 0:
					postAPI("/api/update_location", project_creation, null, {"path":t});
					break;
				case 1:
					postAPI("/api/update_location", project_menu, null, {"name":prjname, "path":t});
					break;
				case 2:
					postAPI("/api/import", project_menu, null, {name:prjname, path:t});
					break;
				case 3:
					postAPI("/api/import_rpgmtrans", project_menu, null, {name:prjname, path:t});
					break;
				default:
					break;
			}
		}}).innerHTML = t.split("/")[t.split("/").length-1];
	}
	
	set_loading(false);
}