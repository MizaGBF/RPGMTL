// main parts
var bar = null;
var main = null;
var bottom = null;
var top_bar_elems = {}; // contains update_top_bar elements
var tl_style = 2; // for sliding the string areas, there are 7 positions
var loader = null;
var loadertext = null;
var loaderanim = null;
var help = null;
var edit_ori = null;
var edit_times = null;
var edit_tl = null;
var tl_string_length = null;
// global variables
var keypressenabled = false;
var path = null;
var project = {}; // current project
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
	edit_times = document.getElementById("edit-times");
	edit_tl = document.getElementById("edit-tl");
	tl_string_length = document.getElementById("string-length");
	// request the page
	load_location();
}

// used once on startup
// read search params and load a page accordingly
function load_location()
{
	try
	{
		let urlparams = new URLSearchParams(window.location.search);
		let page = urlparams.get("page");
		switch(page)
		{
			case "menu":
			{
				go_project(urlparams.get("name"));
				break;
			}
			case "settings":
			{
				go_settings(urlparams.get("name"), true);
				break;
			}
			case "translator":
			{
				if(urlparams.has("name"))
				{
					go_translator(urlparams.get("name"), true);
				}
				else
				{
					go_translator(null, true);
				}
				break;
			}
			case "browse":
			{
				go_browse(urlparams.get("name"), JSON.parse(b64tos(urlparams.get("params"))), true);
				break;
			}
			case "search_string":
			{
				let p = JSON.parse(b64tos(urlparams.get("params")));
				go_search(urlparams.get("name"), p.path, p.search, true);
				break;
			}
			case "patches":
			{
				go_patches(urlparams.get("name"), true);
				break;
			}
			case "open_patch":
			{
				go_open_patch(urlparams.get("name"), JSON.parse(b64tos(urlparams.get("params"))), true);
				break;
			}
			case "backups":
			{
				go_backups(urlparams.get("name"), true);
				break;
			}
			case "file":
			{
				go_file(urlparams.get("name"), JSON.parse(b64tos(urlparams.get("params"))), true);
				break;
			}
			default:
			{
				go_main();
				break;
			}
		};
	}
	catch(err)
	{
		console.error(err);
		go_main();
	}
}

// Reset major variables
function clear_variables()
{
	keypressenabled = false;
	path = null;
	project = {};
	currentstr = null;
	strtablecache = [];
	lastfileopened = null;
	laststringsearch = null;
	laststringinteracted = 0;
	filebrowsingmode = 0;
}

// utility functions to encode/decode unicode strings to b64
function stob64(str) {
	const uint8 = new TextEncoder().encode(str);
	let binary = "";
	for (let byte of uint8) {
		binary += String.fromCharCode(byte);
	}
	return btoa(binary);
}

function b64tos(b64) {
	const binary = atob(b64);
	const uint8 = new Uint8Array(binary.length);
	for (let i = 0; i < binary.length; i++) {
		uint8[i] = binary.charCodeAt(i);
	}
	return new TextDecoder().decode(uint8);
}

// set data for the browser to memorize the current page
function upate_page_location(page, name, params)
{
	if(page == null)
	{
		history.pushState(null, '', window.location.pathname);
	}
	else
	{
		let urlparams = new URLSearchParams("");
		urlparams.set("page", page);
		if(name != null)
		{
			urlparams.set("name", name);
			if(params != null)
			{
				urlparams.set("params", stob64(JSON.stringify(params)));
			}
		}
		let newRelativePathQuery = window.location.pathname + '?' + urlparams.toString();
		history.pushState(null, '', newRelativePathQuery);
	}
}

// for keyboard Space shortcut detection during file editing
document.addEventListener('keydown', function(e)
{
	if(loader.style.display == null)
		return;
	if(keypressenabled) // flag to enable this function
	{
		if(e.code == 'Space' && strtablecache.length > 0 && e.target.tagName != "TEXTAREA") // check if space key was pressed and not on textarea
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
				e.preventDefault();
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
				e.preventDefault();
			}
		}
	}
});

// create and add a new element to a node, and return it
// support various parameters
function add_to(node, tagName, {cls = [], id = null, title = null, onload = null, onclick = null, onerror = null, br = true}={})
{
	let tag = document.createElement(tagName);
	for(let i = 0; i < cls.length; ++i)
		tag.classList.add(cls[i]);
	if(title) tag.title = title;
	if(id) tag.id = id;
	if(onload) tag.onload = onload;
	if(onclick) tag.onclick = onclick;
	if(onerror) tag.onerror = onerror;
	if(node) node.appendChild(tag);
	if(br) node.appendChild(document.createElement("br"));
	return tag;
}

function add_button(node, title, img = null, callback = null)
{
	let btn = add_to(node, "div", {cls:["interact", "button"], title:title, onclick:callback, br:false});
	btn.style.backgroundPosition = "6px 0px";
	btn.style.backgroundRepeat = "no-repeat";
	if(img != null)
		btn.style.backgroundImage = "url(\"" + img + "\")";
	return btn;
}

function add_interaction(node, innerHTML, callback)
{
	let interaction = add_to(node, "div", {cls:["interact", "text-wrapper"], onclick:callback});
	interaction.innerHTML = innerHTML;
	return interaction;
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

// make a POST request
// About callbacks:
// success is called on success
// failure is called on failure
function post(url, success = null, failure = null, payload = {})
{
	set_loading(true);
	fetch(
		url,
		{
			method: "POST", // Specify the HTTP method
			headers: {"Content-Type": "application/json;charset=UTF-8"},
			body: JSON.stringify(payload)
		}
	).then(
		response => {
			try
			{
				response.json().then((json) => {
					process_call(json, success, failure);
				});
			} catch(err) {
				console.error("Unexpected error", err.stack);
				set_loading_text("An unexpected error occured.<br>" + err.stack + "<br><br>Refresh the page.<br>Make sure to report the bug if the issue continue.");
			}
		}
	);
	// note: check if catch is needed?
}

// display a popup with the given string for 4s
function push_popup(string)
{
	let div = document.createElement('div');
	div.className = 'popup';
	div.innerHTML = string;
	document.body.appendChild(div);
	setTimeout(clear_popup, 4000, div);
}

// remove a popup
function clear_popup(popup)
{
	popup.parentNode.removeChild(popup);
}

// get ready to draw new main page
function new_page()
{
	set_loading(false);
	return document.createDocumentFragment();
}

// update the main area with a fragment
function update_main(fragment)
{
	/*
		use requestAnimationFrame to make sure the fragment is properly calculated,
		to avoid weird flicker/wobble from the CSS kicking in
	*/
    return new Promise((resolve, reject) => {
        requestAnimationFrame(() => {
			main.innerHTML = "";
			main.appendChild(fragment);
			
			// Set initial focus
			const firstFocusableElement = main.querySelector('input, select, textarea, [tabindex="0"], a, button');
			if(firstFocusableElement) // Note: placeholder for future keyboard navigation
			{
				firstFocusableElement.focus();
			}
			else
			{
				// If no specific focusable element, try focusing the main content area
				main.focus();
			}
            resolve(); 
        });
    });
}

// generitc function to process the result of requests
function process_call(json, success, failure)
{
	try
	{
		if("message" in json)
			push_popup(json["message"]);
		if(json["result"] == "ok") // good result
		{
			if("name" in json["data"] && "config" in json["data"]) // check data content (note: data MUST be present)
			{
				// keep project infos up to date
				project.name = json["data"]["name"];
				project.config = json["data"]["config"];
				project.version = json["data"]["config"]["version"];
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

/* All purpose function to update the top bar
	- title is the title to be displayed
	- back_callback is the onclick callback of the top left button
	- help_callback is the onclick callback of the top right button. If null, the button isn't displayed
	- additions allow other buttons to appear (or not), set the proper key with a non-zero value:
		- shutdown : Change the top left button to the shutdown icon
		- home: Add the Home button on the top left
		- project: Add the Project button on the top left
		- github: Add the Github button on the top right
		- refresh: Add the Refresh button on the top right. Require refresh_callback to be provided with.
		- slider: Add the Slider button on the top right
		- file_nav: Add Previous and Next file buttons on the top right. Require file_nav_next_callback and file_nav_previous_callback.
*/
function update_top_bar(title, back_callback, help_callback = null, additions = {})
{
	if(!top_bar_elems.back) // meaning empty, initialization
	{
		let fragment = document.createDocumentFragment();
		top_bar_elems.back = add_button(fragment, "Back", null, null);
		top_bar_elems.title = add_to(fragment, "div", {cls:["inline", "text-wrapper"], br:false});
		top_bar_elems.spacer = add_to(fragment, "div", {cls:["barfill"], br:false});
		top_bar_elems.help = add_button(fragment, "Help", "assets/images/help.png", null);
		bar.appendChild(fragment);
	}
	// set title
	top_bar_elems.title.innerText = title;
	// set back callback
	top_bar_elems.back.onclick = back_callback;
	// set help callback
	if(help_callback == null)
	{
		top_bar_elems.help.style.display = "none";
	}
	else
	{
		top_bar_elems.help.onclick = help_callback;
		top_bar_elems.help.style.display = "";
	}
	// set back button to shutdown
	if(additions.shutdown)
	{
		if(top_bar_elems.back.style.backgroundImage != "url(\"assets/images/shutdown.png\")")
			top_bar_elems.back.style.backgroundImage = "url(\"assets/images/shutdown.png\")";
	}
	else
	{
		if(top_bar_elems.back.style.backgroundImage != "url(\"assets/images/back.png\")")
			top_bar_elems.back.style.backgroundImage = "url(\"assets/images/back.png\")";
	}
	// home button
	if(additions.home)
	{
		if(!top_bar_elems.home)
		{
			top_bar_elems.home = add_button(null, "Project Select Page", "assets/images/home.png", function(){
				bottom.style.display = "none";
				go_main();
			});
			top_bar_elems.back.after(top_bar_elems.home);
		}
	}
	else
	{
		if(top_bar_elems.home)
		{
			if(top_bar_elems.home.parentNode)
				top_bar_elems.home.parentNode.removeChild(top_bar_elems.home);
			delete top_bar_elems.home;
		}
	}
	// project button
	if(additions.project)
	{
		if(!top_bar_elems.project)
		{
			top_bar_elems.project = add_button(null, "Project Menu", "assets/images/project.png", function(){
				bottom.style.display = "none";
				go_project(project.name);
			});
			if(top_bar_elems.home)
				top_bar_elems.home.after(top_bar_elems.project);
			else
				top_bar_elems.back.after(top_bar_elems.project);
		}
	}
	else
	{
		if(top_bar_elems.project)
		{
			if(top_bar_elems.project.parentNode)
				top_bar_elems.project.parentNode.removeChild(top_bar_elems.project);
			delete top_bar_elems.project;
		}
	}
	// github button
	if(additions.github)
	{
		if(!top_bar_elems.github)
		{
			top_bar_elems.github = add_button(null, "Github Page", "assets/images/github.png", function(){
				window.open("https://github.com/MizaGBF/RPGMTL", "_blank")
			});
			top_bar_elems.help.before(top_bar_elems.github);
		}
	}
	else
	{
		if(top_bar_elems.github)
		{
			if(top_bar_elems.github.parentNode)
				top_bar_elems.github.parentNode.removeChild(top_bar_elems.github);
			delete top_bar_elems.github;
		}
	}
	// refresh button
	if(additions.refresh && additions.refresh_callback)
	{
		if(!top_bar_elems.refresh)
		{
			top_bar_elems.refresh = add_button(null, "Refresh", "assets/images/update.png", additions.refresh_callback);
			top_bar_elems.help.before(top_bar_elems.refresh);
		}
		else top_bar_elems.refresh.onclick = additions.refresh_callback;
	}
	else
	{
		if(top_bar_elems.refresh)
		{
			if(top_bar_elems.refresh.parentNode)
				top_bar_elems.refresh.parentNode.removeChild(top_bar_elems.refresh);
			delete top_bar_elems.refresh;
		}
	}
	// slider button
	if(additions.slider)
	{
		if(!top_bar_elems.slider)
		{
			top_bar_elems.slider = add_button(null, "Slide String Areas", "assets/images/tl_slide.png", function(){
				tl_style = (tl_style + 1) % 5;
				/* Positions
					10% 25% 45% 65% 80%
				*/
				const percents = [10, 25, 45, 65, 80];
				document.documentElement.style.setProperty('--ori-width', percents[tl_style] + "%");
				document.documentElement.style.setProperty('--tl-width', (90 - percents[tl_style]) + "%");
			});
			if(top_bar_elems.refresh)
				top_bar_elems.refresh.before(top_bar_elems.slider);
			else
				top_bar_elems.help.before(top_bar_elems.slider);
		}
	}
	else
	{
		if(top_bar_elems.slider)
		{
			if(top_bar_elems.slider.parentNode)
				top_bar_elems.slider.parentNode.removeChild(top_bar_elems.slider);
			delete top_bar_elems.slider;
		}
	}
	// file navigation
	if(additions.file_nav)
	{
		if(!top_bar_elems.next_file)
		{
			top_bar_elems.next_file = add_button(null, "Next File", "assets/images/next.png", additions.file_nav_next_callback);
			top_bar_elems.slider.before(top_bar_elems.next_file);
		}
		else top_bar_elems.next_file.onclick = additions.file_nav_next_callback;
		if(!top_bar_elems.prev_file)
		{
			top_bar_elems.prev_file = add_button(null, "Previous File", "assets/images/previous.png", additions.file_nav_previous_callback);
			top_bar_elems.next_file.before(top_bar_elems.prev_file);
		}
		else top_bar_elems.prev_file.onclick = additions.file_nav_previous_callback;
	}
	else
	{
		if(top_bar_elems.next_file)
		{
			if(top_bar_elems.next_file.parentNode)
				top_bar_elems.next_file.parentNode.removeChild(top_bar_elems.next_file);
			delete top_bar_elems.next_file;
		}
		if(top_bar_elems.prev_file)
		{
			if(top_bar_elems.prev_file.parentNode)
				top_bar_elems.prev_file.parentNode.removeChild(top_bar_elems.prev_file);
			delete top_bar_elems.prev_file;
		}
	}
}

// handle result of /api/main
function project_list(data)
{
	upate_page_location(null, null, null);
	clear_variables(); // in case we got here from an error
	
	// top bar
	update_top_bar(
		"RPGMTL v" + data["verstring"],
		function(){ // back callback
			if(window.event.ctrlKey | window.confirm("Shutdown RPGMTL?\nEverything will be saved."))
			{
				post("/api/shutdown", function(_unused_) {
					bar.innerHTML = "";
					let fragment = new_page();
					add_to(fragment, "div", {cls:["title"]}).innerText = "RPGMTL has been shutdown";
					update_main(fragment);
				});
			}
		},
		function(){ // help
			help.innerHTML = "<ul>\
				<li>Load an existing <b>Project</b> or create a new one.</li>\
				<li>Click twice on the Shutdown button to stop RPGMTL remotely.</li>\
			</ul>";
			help.style.display = "";
		},
		{
			shutdown:1,
			github:1
		}
	);
	
	// main part
	fragment = new_page();
	add_to(fragment, "div", {cls:["title"]}).innerHTML = "Project List";
	if(data["list"].length > 0) // list projects
	{
		for(let i = 0; i < data["list"].length; ++i)
		{
			const t = data["list"][i];
			add_interaction(fragment, data["list"][i], function(){
				go_project(t);
			});
		}
	}
	add_to(fragment, "div", {cls:["spacer"]});
	// add buttons
	add_interaction(fragment, '<img src="assets/images/new.png"> New Project', function(){
		local_browse("Create a project", "Select a Game executable.", 0);
	});
	add_interaction(fragment, '<img src="assets/images/setting.png"> Global Settings', function(){
		go_settings(null, true);
	});
	add_interaction(fragment, '<img src="assets/images/translate.png"> Default Translator', function(){
		go_translator(null, true);
	});
	add_to(fragment, "div", {cls:["spacer"]});
	// quick links
	if(data["history"].length > 0) // list last browsed Files
	{
		add_to(fragment, "div", {cls:["title", "left"], br:false}).innerHTML = "Last Accessed Files";
		for(let i = 0; i < data["history"].length; ++i)
		{
			const c_entry = data["history"][i];
			add_interaction(fragment, c_entry[0] + ": " + c_entry[1], function(){
				go_file(c_entry[0], c_entry[1], true);
			});
		}
	}
	update_main(fragment);
}

// display settings for /api/settings
function setting_menu(data)
{
	try
	{
		const is_project = "config" in data;
		
		upate_page_location("settings", (is_project ? project.name : null), null);
		
		// top bar
		update_top_bar(
			(is_project ? project.name + " Settings" : "Default Settings"),
			function(){ // back callback
				if(is_project)
					project_menu();
				else
					go_main();
			},
			function(){ // help
				help.innerHTML = "<ul>\
					<li>Some settings might require you to extract your project strings again, be careful to not lose progress.</li>\
					<li><b>Default</b> Settings are your projects defaults.</li>\
					<li><b>Project</b> Settings override <b>Default</b> Settings when modified.</li>\
				</ul>";
				help.style.display = "";
			},
			{
				home:is_project
			}
		);
		
		// main part
		fragment = new_page();
		let layout = data["layout"];
		let settings = data["settings"];
		
		if(is_project) // add button to reset settings of THIS project
		{
			add_interaction(fragment, '<img src="assets/images/trash.png"> Reset All Settings to Global', function(){
				post("/api/update_settings", function(result_data) {
					push_popup("The Project Settings have been reset to Global Settings.");
					project_menu();
				}, null, {name:project.name});
			});
		}
		
		let count = 0;
		// go over received setting menu layout
		for(const [file, fsett] of Object.entries(layout))
		{
			// add plugin name
			add_to(fragment, "div", {cls:["title", "left"], br:false}).innerHTML = file + " Plugin settings";
			// and description if it exists
			if(file in data["descriptions"] && data["descriptions"][file] != "")
				add_to(fragment, "div", {cls:["left", "interact-group", "smalltext"]}).innerText = data["descriptions"][file];
			// go over options
			for(const [key, fdata] of Object.entries(fsett))
			{
				if(fdata[1] == "bool")
				{
					add_to(fragment, "div", {cls:["settingtext"], br:false}).innerHTML = fdata[0];
					// add a simple toggle
					const elem = add_button(fragment, "Set", "assets/images/confirm.png", function(){
						let callback = function(result_data) {
							push_popup("The setting has been updated.");
							set_loading(false);
							if(key in result_data["settings"])
								elem.classList.toggle("green", result_data["settings"][key]);
						};
						if(is_project)
						{
							post("/api/update_settings", callback, null, {name:project.name, key:key, value:!elem.classList.contains("green")});
						}
						else
						{
							post("/api/update_settings", callback, null, {key:key, value:!elem.classList.contains("green")});
						}
					});
					fragment.appendChild(document.createElement("br"));
					if(key in settings)
						elem.classList.toggle("green", settings[key]);
					++count;
				}
				else // other text/number types
				{
					add_to(fragment, "div", {cls:["settingtext"]}).innerHTML = fdata[0];
					if(fdata[2] == null) // text input
					{
						/*
							text: div (not textarea, we want resize) & no return key validation
							str: standard input text
							password: input password
							int/float: standard input text
						*/
						// add an input element
						const input = (
							fdata[1] == "text" ?
							add_to(fragment, "div", {cls:["input", "smallinput", "inline"], br:false}) :
							add_to(fragment, "input", {cls:["input", "smallinput"], br:false})
						);
						switch(fdata[1])
						{
							case "password":
							{
								input.type = "password";
								break;
							}
							case "str":
							{
								input.type = "text";
								break;
							}
							case "text":
							{
								input.contentEditable="plaintext-only";
								break;
							}
						}
						// and confirmation button
						const elem = add_button(fragment, "Set", "assets/images/confirm.png", function(){
							let val = "";
							switch(fdata[1]) // make sure our value is what RPGMTL wants
							{
								case "int":
									if(isNaN(input.value) || isNaN(parseFloat(input.value)))
									{
										push_popup("The value isn't a valid integer.");
										return;
									}
									val = Math.floor(parseFloat(input.value));
									break;
								case "float":
									if(isNaN(input.value) || isNaN(parseFloat(input.value)))
									{
										push_popup("The value isn't a valid floating number.");
										return;
									}
									val = parseFloat(input.value);
									break;
								default:
									val = input.value;
									break;
							}
							let callback = function(result_data) {
								push_popup("The setting has been updated.");
								set_loading(false);
								if(key in result_data["settings"])
									input.value = result_data["settings"][key];
							};
							if(is_project)
							{
								post("/api/update_settings", callback, null, {name:project.name, key:key, value:val});
							}
							else
							{
								post("/api/update_settings", callback, null, {key:key, value:val});
							}
						});
						fragment.appendChild(document.createElement("br"));
						if(fdata[1] != "text")
						{
							// add listener to detect keypress
							input.addEventListener('keypress', function(event) {
								if (event.key === 'Enter')
								{
									event.preventDefault();
									elem.click();
								}
							});
						}
						
						if(key in settings)
							input.value = settings[key];
						++count;
					}
					else // choice selection
					{
						// add select and option elements
						const sel = add_to(fragment, "select", {cls:["input", "smallinput"], br:false});
						for(let i = 0; i < fdata[2].length; ++i)
						{
							let opt = add_to(sel, "option");
							opt.value = fdata[2][i];
							opt.textContent = fdata[2][i];
						}
						// and confirmation button
						const elem = add_button(fragment, "Set", "assets/images/confirm.png", function()
						{
							let callback = function(result_data) {
								push_popup("The setting has been updated.");
								set_loading(false);
								if(key in result_data["settings"])
									sel.value = result_data["settings"][key];
							};
							if(is_project)
							{
								post("/api/update_settings", callback, null, {name:project.name, key:key, value:sel.value});
							}
							else
							{
								post("/api/update_settings", callback, null, {key:key, value:sel.value});
							}
						});
						if(key in settings)
							sel.value = settings[key];
						++count;
					}
				}
			}
		}
		if(count == 0)
			add_to(fragment, "div", {cls:["title", "left"]}).innerHTML = "No settings available for your Plugins";
		update_main(fragment);
	}
	catch(err)
	{
		console.error("Exception thrown", err.stack);
		push_popup("An unexpected error occured.");
		go_main();
	}
}

// translator pick menu /api/translator
function translator_menu(data)
{
	try
	{
		const is_project = "config" in data;
		
		upate_page_location("translator", (is_project ? project.name : null), null);
		
		// top bar
		update_top_bar(
			(is_project ? project.name + " Translators" : "Global Translators"),
			function(){ // back callback
				if(is_project)
					project_menu();
				else
					go_main();
			},
			function(){ // help
				help.innerHTML = "<ul>\
					<li>Select the Translator Plugin to use.</li>\
					<li><b>Default</b> Translator is used by default.</li>\
					<li><b>Project</b> Translator override the <b>Default</b> when modified.</li>\
				</ul>";
				help.style.display = "";
			},
			{
				home:is_project
			}
		);
		
		// main part
		fragment = new_page();
		let list = data["list"]; // translator plugin list
		let possibles = ["current", "batch"];
		let possibles_text = ["Single Translation Button", "Translate this File Button"];
		for(let t = 0; t < possibles.length; ++t)
		{
			if(list.length == 0)
			{
				add_to(fragment, "div", {cls:["title", "left"]}).innerHTML = "No Translator Plugin available";
				break;
			}
			else
			{
				if(t == 0 && is_project) // add button to reset project setting (Only at the top)
				{
					add_interaction(fragment, '<img src="assets/images/trash.png"> Use RPGMTL Default', function(){
						post("/api/update_translator", function(result_data) {
							push_popup("The Project Translator have been reset to the default.");
							project_menu();
						}, null, {name:project.name});
					});
				}
				// add text
				add_to(fragment, "div", {cls:["title", "left"]}).innerHTML = possibles_text[t];
				// add select and option elements
				const sel = add_to(fragment, "select", {cls:["input", "smallinput"], br:false});
				for(let i = 0; i < list.length; ++i)
				{
					let opt = add_to(sel, "option");
					opt.value = list[i];
					opt.textContent = list[i];
				}
				const tindex = t;
				// and confirmation button
				const elem = add_button(fragment, "Set", "assets/images/confirm.png", function()
				{
					let callback = function(result_data) {
						push_popup("The setting has been updated.");
						set_loading(false);
					};
					if(is_project)
					{
						post("/api/update_translator", callback, null, {name:project.name, value:sel.value, index:tindex});
					}
					else
					{
						post("/api/update_translator", callback, null, {value:sel.value, index:tindex});
					}
				});
				sel.value = data[possibles[t]];
			}
		}
		update_main(fragment);
	}
	catch(err)
	{
		console.error("Exception thrown", err.stack);
		push_popup("An unexpected error occured.");
		go_main();
	}
}

// project creation /api/update_location
function project_creation(data)
{
	// don't update upate_page_location here
	
	if(data["path"] == "" || data["path"] == null)
	{
		go_main();
	}
	else
	{
		path = data["path"];
		// top bar
		update_top_bar(
			"Create a new Project",
			function(){ // back callback
				go_main();
			},
			function(){ // help
				help.innerHTML = "<ul>\
					<li>The Project Name has little importance, just make sure you know what it refers to.</li>\
					<li>If already taken, a number will be added after the name.</li>\
				</ul>";
				help.style.display = "";
			}
		);
		
		// main part
		fragment = new_page();
		add_to(fragment, "div", {cls:["title", "left"]}).innerHTML = "Folder/Project Name";
		
		// project name input element
		let input = add_to(fragment, "input", {cls:["input"]});
		input.type = "text";
		
		let tmp = path.split("/"); // set input default value
		if(tmp.length >= 1)
			input.value = tmp[tmp.length-1];
		else
			input.value = "Project";
		
		// confirm button
		add_interaction(fragment, '<img src="assets/images/confirm.png"> Create', function(){
			set_loading_text("Creating the project...");
			if(input.value.trim() != "")
			{
				go_new_project(path, input.value);
			}
		});
		update_main(fragment);
	}
}

// display project options (called by many API and more, data is optional and unused)
function project_menu(data = null)
{
	try
	{
		upate_page_location("menu", project.name, null);
		
		// top bar
		update_top_bar(
			project.name,
			function(){ // back callback
				go_main();
			},
			function(){ // help
				help.innerHTML = "<ul>\
					<li><b>Browse Files</b> to browse and translate strings.</li>\
					<li><b>Add a Fix</b> to add Python patches to apply during the release process (Check the README for details).</li>\
					<li><b>Replace Strings in batch</b> open a menu to replace parts of strings by others, in your existing translations.</li>\
					<li>Set your <b>Settings before<b/> extracting the strings.</li>\
					<li><b>Unload the Project<b/> if you must do modifications on the local files, using external scripts or whatever.</li>\
				</ul>\
				<ul>\
					<li><b>Update the Game Files</b> if it got updated or if you need to re-copy the files.</li>\
					<li><b>Extract the Strings</b> if you need to extract them from Game Files.</li>\
					<li><b>Release a Patch</b> to create a copy of Game files with your translated strings. They will be found in the <b>release</b> folder.</li>\
				</ul>\
				<ul>\
					<li><b>Import Strings from RPGMTL</b> to import strings from RPGMTL projects from any version.</li>\
					<li><b>Strings Backups</b> to open the list of backups if you need to revert the project data to an earlier state.</li>\
				</ul>";
				help.style.display = "";
			},
			{
				home:1
			}
		);
		
		// main part
		// here we add various buttons
		// some only appear if files have been parsed
		fragment = new_page();
		add_to(fragment, "div", {cls:["title"]}).innerHTML = project.name;
		add_to(fragment, "div", {cls:["title", "left"]}).innerHTML = "Game Folder: " + project.config["path"];
		if(project.config.files)
		{
			add_interaction(fragment, '<img src="assets/images/folder.png"> Browse Files', function(){
				go_browse(project.name, "");
			});
			add_interaction(fragment, '<img src="assets/images/bandaid.png"> Add a Fix', function(){
				go_patches(project.name);
			});
			add_interaction(fragment, '<img src="assets/images/copy.png"> Replace Strings in batch', function(){
				replace_page();
			});
		}
		add_interaction(fragment, '<img src="assets/images/setting.png"> Project Settings', function(){
			go_settings(project.name);
		});
		add_interaction(fragment, '<img src="assets/images/translate.png"> Project Translator', function(){
			go_translator(project.name);
		});
		add_interaction(fragment, '<img src="assets/images/cancel.png"> Unload the Project', function(){
			post("/api/unload", go_main, null, {name:project.name});
		});
		add_to(fragment, "div", {cls:["spacer"]});
		add_interaction(fragment, '<img src="assets/images/update.png"> Update the Game Files', function(){
			local_browse("Update project files", "Select the Game executable.", 1);
		});
		add_interaction(fragment, '<img src="assets/images/export.png"> Extract the Strings', function(){
			set_loading_text("Extracting, be patient...");
			post("/api/extract", project_menu, go_main, {name:project.name});
		});
		if(project.config.files)
		{
			add_interaction(fragment, '<img src="assets/images/release.png"> Release a Patch', function(){
				set_loading_text("The patch is being generated in the release folder...");
				post("/api/release", project_menu, null, {name:project.name});
			});
			add_to(fragment, "div", {cls:["spacer"]});
			add_interaction(fragment, '<img src="assets/images/copy.png"> String Backups', function(){
				go_backups(project.name);
			});
			add_interaction(fragment, '<img src="assets/images/import.png"> Import Strings from RPGMTL', function(){
				local_browse("Import RPGMTL", "Select an old RPGMTL strings file.", 2);
			});
			add_interaction(fragment, '<img src="assets/images/import.png"> Import Strings from RPGMakerTrans v3', function(){
				local_browse("Import RPGMAKERTRANSPATCH", "Select a RPGMAKERTRANSPATCH file.", 3);
			});
			add_to(fragment, "div", {cls:["spacer"]});
		}
		update_main(fragment);
	}
	catch(err)
	{
		console.error("Exception thrown", err.stack);
		push_popup("An unexpected error occured.");
		go_main();
	}
}

// generic function to add a search bar on top of the browse file page
function addSearchBar(node, bp, defaultVal = null)
{
	// input element
	const input = add_to(node, "input", {cls:["input", "smallinput"], br:false});
	input.placeholder = "Search a string";
	if(defaultVal != null)
		input.value = defaultVal;
	else if(laststringsearch != null) // set last string searched if not null
		input.value = laststringsearch;
	else
		input.value = "";
	// add confirm button
	const button = add_button(node, "Search", "assets/images/search.png", function(){
		if(input.value != "")
		{
			post("/api/search_string", string_search, null, {name:project.name, path:bp, search:input.value});
		}
	});
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
	let urlparams = new URLSearchParams("");
	urlparams.set("page", "search_string");
	urlparams.set("name", project.name);
	urlparams.set("params", stob64(JSON.stringify({name:project.name, path:project.last_data["path"], search:document.getElementById('edit-ori').textContent})));
	window.open(window.location.pathname + '?' + urlparams.toString(), '_blank').focus(); // open in another tab
}

// open folder /api/browse
function browse_files(data)
{
	try
	{
		keypressenabled = false;
		laststringsearch = null;
		const bp = data["path"];
		upate_page_location("browse", project.name, bp);
		// top bar
		update_top_bar(
			"Path: " + bp,
			function(){ // back callback
				let returnpath = bp.includes('/') ? bp.split('/').slice(0, bp.split('/').length-2).join('/')+'/' : "";
				// returnpath is the path of the parent folder
				if(bp == "") // current folder is the root, so back to menu
					project_menu();
				else
				{
					if(returnpath == '/') returnpath = ''; // if return path is a single slash, set to empty first
					go_browse(project.name, returnpath);
				}
			},
			function(){ // help
				help.innerHTML = "<ul>\
					<li>CTRL+Click on a file to <b>disable</b> it, it won't be patched during the release process.</li>\
					<li>The string counts and completion percentages update slowly in the background, don't take them for granted.</li>\
				</ul>";
				help.style.display = "";
			},
			{
				home:1,
				project:1,
				refresh:1,
				refresh_callback:function(){
					go_browse(project.name, bp);
				}
			}
		);
		
		// main part
		fragment = new_page();
		add_to(fragment, "div", {cls:["title"]}).innerHTML = project.name;
		// add the string search
		addSearchBar(fragment, bp);
		
		// add completion indicator (filled at the bottom)
		let completion = add_to(fragment, "div", {cls:["title", "left"]});
		let fstring = 0;
		let ftotal = 0;
		let fcount = 0;
		
		add_to(fragment, "div", {cls:["title", "left"]}).innerHTML = bp;
		// go over folders
		for(let i = 0; i < data["folders"].length; ++i)
		{
			const t = data["folders"][i];
			let div = add_to(fragment, "div", {cls:["interact"]});
			if(t == "..") // special one indicating we aren't on the root level
			{
				div.innerHTML = '<img src="assets/images/back.png"> ..';
			}
			else if(project.config["files"][t.slice(0, -1)] != undefined) // for archive type files
			{
				div.innerHTML = '<img src="assets/images/archive.png"> ' + t;
				div.classList.add("archive");
			}
			else
			{
				div.innerHTML = '<img src="assets/images/folder.png"> ' + t;
			}
			div.onclick = function() // add callback
			{
				if(t == "..") // used for the "parent folder" button
				{
					let s = bp.split("/"); // at least 2 elements in s means there is one slash in the path, i.e. we aren't in the root level
					if(s.length == 2)
					{
						go_browse(project.name, "");
					}
					else
					{
						go_browse(project.name, s.slice(0, s.length-2).join("/") + "/");
					}
				}
				else // open whatever folder it is
				{
					go_browse(project.name, t);
				}
			};
		}
		add_to(fragment, "div", {cls:["title", "left"]}).innerHTML = "List of Files";
		// possible class sets
		let cls = [
			["interact", "text-wrapper"],
			["interact", "text-wrapper", "disabled"]
		];
		let scrollTo = null; // contains element to scroll to
		for(const [key, value] of Object.entries(data["files"]))
		{
			// add button
			let button = add_to(fragment, "div", {cls:cls[+value], br:false, id:"text:"+key, onclick:function(){
				if(window.event.ctrlKey) // ignore shortcut
				{
					post("/api/ignore_file", update_file_list, null, {name:project.name, path:key, state:+!this.classList.contains("disabled")});
				}
				else
				{
					set_loading_text("Opening " + key + "...");
					go_file(project.name, key);
				}
			}});
			// add completion indicator
			let total = project.config["files"][key]["strings"] - project.config["files"][key]["disabled_strings"];
			let count = project.config["files"][key]["translated"];
			let percent = total > 0 ? ", " + (Math.round(10000 * count / total) / 100) + "%)" : ")";
			
			if(!value) // add to folder completion indicator
			{
				fstring += project.config["files"][key]["strings"];
				ftotal += total;
				fcount += count;
			}
			
			if(count == total) // add complete class if no string left to translate
				button.classList.add("complete");
			button.textContent = key + ' (' + project.config["files"][key]["strings"] + percent; // set text
			if(key == lastfileopened) // if this is the last opened file
				scrollTo = button; // store it
		}
		add_to(fragment, "div", {cls:["spacer"]});
		add_to(fragment, "div", {cls:["spacer"]});
		add_to(fragment, "div", {cls:["spacer"]});
		// set folder completion indicator
		let percent = ftotal > 0 ? ', ' + (Math.round(10000 * fcount / ftotal) / 100) + '%' : '';
		completion.textContent = "Current Total: " + fstring + " strings" + percent;
		update_main(fragment).then(() => {
			if(scrollTo != null) // scroll to last opened file
				scrollTo.scrollIntoView();
		});
		lastfileopened = null; // and clear it
	}
	catch(err)
	{
		lastfileopened = null;
		console.error("Exception thrown", err.stack);
		push_popup("An unexpected error occured.");
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
		laststringsearch = data["search"];
		upate_page_location("search_string", project.name, {"path":bp, "search":laststringsearch});
		// top bar
		update_top_bar(
			"Search Results",
			function(){ // back callback
				if(bp in data["files"])
				{
					go_file(project.name, data["path"]);
				}
				else
				{
					go_browse(project.name, data["path"]);
				}
			},
			function(){ // help
				help.innerHTML = "<ul>\
					<li>Your search results are displayed here.</li>\
				</ul>";
				help.style.display = "";
			},
			{
				home:1,
				project:1
			}
		);
		
		// main part
		fragment = new_page();
		add_to(fragment, "div", {cls:["title"]}).innerHTML = project.name;
		addSearchBar(fragment, bp, data["search"]);
		
		add_to(fragment, "div", {cls:["title", "left"]}).innerHTML = "Search Results";
		let cls = [
			["interact", "text-wrapper"],
			["interact", "text-wrapper", "disabled"]
		];
		// list files
		for(const [key, value] of Object.entries(data["files"]))
		{
			let button = add_to(fragment, "div", {cls:cls[+value], br:false, id:"text:"+key, onclick:function(){
				if(window.event.ctrlKey) // disable shortcut
				{
					post("/api/ignore_file", update_file_list, null, {name:project.name, path:key, state:+!this.classList.contains("disabled")});
				}
				else
				{
					set_loading_text("Opening " + key + "...");
					go_file(project.name, key);
				}
			}});
			let total = project.config["files"][key]["strings"] - project.config["files"][key]["disabled_strings"];
			let count = project.config["files"][key]["translated"];
			let percent = total > 0 ? ', ' + (Math.round(10000 * count / total) / 100) + '%)' : ')';
			if(count == total)
				button.classList.add("complete");
			button.innerHTML = key + ' (' + total + " strings" + percent;
		}
		update_main(fragment);
	}
	catch(err)
	{
		console.error("Exception thrown", err.stack);
		push_popup("An unexpected error occured.");
		project_menu();
	}
}

// open fix list /api/patches
function browse_patches(data)
{
	try
	{
		upate_page_location("patches", project.name, null);
		// top part
		update_top_bar(
			project.name,
			function(){ // back callback
				project_menu();
			},
			function(){ // help
				help.innerHTML = "<ul>\
					<li>Select an existing patch/fix or create a new one.</li>\
					<li>The patch/fix will be applied on all files whose name contains the patch/fix name.</li>\
					<li>The patch/fix code must be valid <b>Python</b> code, refer to the <b>README</b> for details.</li>\
				</ul>";
				help.style.display = "";
			}
		);
		
		// main part
		fragment = new_page();
		add_to(fragment, "div", {cls:["title"]}).innerHTML = project.name;
		add_to(fragment, "div", {cls:["title", "left"]}).innerHTML = "Fix List";
		// list patches
		for(const [key, value] of Object.entries(project.config["patches"]))
		{
			// add button to open
			add_interaction(fragment, '<img src="assets/images/bandaid.png"> ' + key, function() {
				go_open_patch(project.name, key);
			});
		}
		add_to(fragment, "div", {cls:["spacer"]});
		// add create button
		add_interaction(fragment, '<img src="assets/images/new.png"> Create', function() {
			edit_patch({});
		});
		update_main(fragment);
	}
	catch(err)
	{
		console.error("Exception thrown", err.stack);
		push_popup("An unexpected error occured.");
		project_menu();
	}
}

// edit a fix /api/open_patch
function edit_patch(data)
{
	try
	{
		const key = data["key"]; // patch key. Note: CAN be null
		if(key != null)
			upate_page_location("open_patch", project.name, key);
		// top bar
		update_top_bar(
			"Create a Fix",
			function(){ // back callback
				go_patches(project.name);
			},
			function(){ // help
				help.innerHTML = "<ul>\
					<li>Select an existing patch/fix or create a new one.</li>\
					<li>The patch/fix will be applied on all files whose name contains the patch/fix name.</li>\
					<li>The patch/fix code must be valid <b>Python</b> code, refer to the <b>README</b> for details.</li>\
				</ul>";
				help.style.display = "";
			},
			{
				home:1
			}
		);
		
		// main part
		fragment = new_page();
		// add various input and text elements
		add_to(fragment, "div", {cls:["title"]}).innerHTML = project.name;
		add_to(fragment, "div", {cls:["title", "left"]}).innerHTML = "Filename match";
		add_to(fragment, "input", {cls:["input"], id:"filter"}).type = "text";
		add_to(fragment, "div", {cls:["title", "left"]}).innerHTML = "Python Code";
		add_to(fragment, "div", {cls:["input"], id:"fix"}).contentEditable = "plaintext-only";
		// add confirm button
		add_interaction(fragment, '<img src="assets/images/confirm.png"> Confirm', function() {
			let newkey = document.getElementById("filter").value;
			let code = document.getElementById("fix").textContent;
			if(newkey.trim() != "" && code.trim() != "")
			{
				post("/api/update_patch", browse_patches, null, {name:project.name, key:key, newkey:newkey, code:code});
			}
			else
			{
				push_popup("At least one field is empty");
			}
		});
		add_interaction(fragment, '<img src="assets/images/trash.png"> Delete', function() {
			post("/api/update_patch", browse_patches, null, {name:project.name, key:key});
		});
		if(key != null)
		{
			fragment.getElementById("filter").value = key;
			fragment.getElementById("fix").textContent = project.config["patches"][key];
		}
		update_main(fragment);
	}
	catch(err)
	{
		console.error("Exception thrown", err.stack);
		push_popup("An unexpected error occured.");
		project_menu();
	}
}

// open backup list /api/backups
function backup_list(data)
{
	try
	{
		upate_page_location("backups", project.name, null);
		// top part
		update_top_bar(
			project.name,
			function(){ // back callback
				project_menu();
			},
			function(){ // help
				help.innerHTML = "<ul>\
					<li>Select an existing backup to use it.</li>\
					<li>Click Twice or CTRL+Click on <b>Use</b> to select the backup.</li>\
					<li>Existing strings.json and its backups will be properly kept, while the selected backup will become the new strings.json.</li>\
				</ul>";
				help.style.display = "";
			},
			{
				home:1
			}
		);
		
		// main part
		fragment = new_page();
		add_to(fragment, "div", {cls:["title"]}).innerHTML = project.name;
		add_to(fragment, "div", {cls:["title", "left"]}).innerHTML = "Backup List";
		if(data["list"].length == 0)
			add_to(fragment, "div", {cls:["title", "left", "block", "inline"], br:false}).innerHTML = "No backup available";
		// list project backups
		for(const elem of data["list"])
		{
			// add button to load it
			add_to(fragment, "div", {cls:["interact", "text-button", "inline"], br:false, onclick:function(){
				if(window.event.ctrlKey || window.confirm("Load this backup?")) // confirmation / shortcut to insta confirm
				{
					post("/api/load_backup", project_menu, null, {name:project.name, file:elem[0]});
				}
			}}).innerHTML = '<img src="assets/images/copy.png"> Use';
			add_to(fragment, "div", {cls:["title", "left", "block", "inline"], br:false}).innerHTML = elem[0];
			// add backup infos
			let size = "";
			if(elem[1] >= 1048576) size = Math.round(elem[1] / 1048576) + "MB";
			else if(elem[1] >= 1024) size = Math.round(elem[1] / 1024) + "KB";
			else size = elem[1] + "B";
			add_to(fragment, "div", {cls:["title", "left", "block", "inline", "smalltext"], br:false}).innerHTML = size;
			add_to(fragment, "div", {cls:["title", "left", "block", "inline", "smalltext"]}).innerHTML = new Date(elem[2]*1000).toISOString().split('.')[0].replace('T', ' ');
		}
		update_main(fragment);
	}
	catch(err)
	{
		console.error("Exception thrown", err.stack);
		push_popup("An unexpected error occured.");
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
			let file = document.getElementById("text:"+key);
			if(file)
			{
				if(value) file.classList.add("disabled");
				else file.classList.remove("disabled");
			}
		}
	}
	catch(err)
	{
		console.error("Exception thrown", err.stack);
		push_popup("An unexpected error occured.");
		project_menu();
	}
}

// Prepare string space for string list
function prepareGroupOn(node, i)
{
	let base = add_to(node, "div", {cls:["interact-group"]}); // base container
	let group = add_to(base, "span", {cls:["smalltext"], id:i}); // group container
	if(project.string_groups[i][0] != "") // add group name OR index
		group.textContent = project.string_groups[i][0];
	else
		group.textContent = "#"+(i+1);
	// iterate over strings of this group
	for(let j = 1; j < project.string_groups[i].length; ++j)
	{
		const span = add_to(base, "span", {cls:["interact", "string-group"]}); // add container
		span.group = i;
		span.string = j;
		
		let marker = add_to(span, "div", {cls:["marker", "inline"], br:false}); // left marker (modified, plugins...)
		
		let original = add_to(span, "pre", {cls:["title", "inline", "smalltext", "string-area", "original"], br:false}); // original string
		original.group = i;
		original.string = j;
		original.textContent = project.strings[project.string_groups[i][j][0]][0];
		const occurence = project.strings[project.string_groups[i][j][0]][2];
		
		let translation = add_to(span, "pre", {cls:["title", "inline", "smalltext", "string-area", "translation"], br:false}); // translated string
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
				post("/api/update_string", update_string_list, null, {setting:1, version:project.version, name:project.name, path:project.last_data["path"], group:this.group, index:this.string});
			}
			else if(window.event.ctrlKey && !window.event.shiftKey && window.event.altKey) // multi disable
			{
				laststringinteracted = tsize;
				set_loading_text("Updating...");
				post("/api/update_string", update_string_list, null, {setting:2, version:project.version, name:project.name, path:project.last_data["path"], group:this.group, index:this.string});
			}
			else if(!window.event.ctrlKey && window.event.shiftKey && !window.event.altKey) // unlink
			{
				if(bottom.style.display == "none")
				{
					laststringinteracted = tsize;
					set_loading_text("Updating...");
					post("/api/update_string", update_string_list, null, {setting:0, version:project.version, name:project.name, path:project.last_data["path"], group:this.group, index:this.string});
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
					push_popup('The String has been copied');
				}
				else push_popup('You need to be on a secure origin to use the Copy button');
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
						push_popup('The String has been copied');
					}
					else push_popup('You need to be on a secure origin to use the Copy button');
				}
				else
				{
					laststringinteracted = tsize;
					// string from project data
					let ss = project.string_groups[span.group][span.string];
					// update bottom part
					// set occurence count
					if(occurence > 1)
						edit_times.textContent = occurence + " occurences of this string in the game";
					else
						edit_times.textContent = "";
					// set original string text
					edit_ori.textContent = project.strings[ss[0]][0];
					// set textarea with current translation
					if(ss[2]) // local/unlinked
					{
						if(ss[1] != null)
							edit_tl.value = ss[1];
						else
							edit_tl.value = project.strings[ss[0]][0]; // default to original if not translated
					}
					else if(project.strings[ss[0]][1] != null) // global
						edit_tl.value = project.strings[ss[0]][1];
					else
						edit_tl.value = project.strings[ss[0]][0]; // default to original if not translated
					// update string-length indicator
					tl_string_length.innerHTML = edit_tl.value.length;
					// make element visible
					bottom.style.display = "";
					// focus
					edit_tl.focus();
					// set this span element as the current string being edited
					if(currentstr != null)
					{
						currentstr.classList.toggle("selected-line", false);
					}
					currentstr = span;
					currentstr.classList.toggle("selected-line", true);
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
		project.strings = data["strings"];
		project.string_groups = data["list"];
		project.last_data = data;
		lastfileopened = data["path"];
		
		upate_page_location("file", project.name, lastfileopened);
		
		// folder path
		const returnpath = lastfileopened.includes('/') ? lastfileopened.split('/').slice(0, lastfileopened.split('/').length-1).join('/')+'/' : "";
		
		// determinate the previous and next file in the same folder
		let prev_file = null;
		let next_file = null;
		let file_same_folder = [];
		for(let f in project.config["files"])
		{
			if((returnpath == "" && !f.includes('/'))
				|| (f.startsWith(returnpath) && !f.substring(returnpath.length).includes('/')))
			{
				file_same_folder.push(f);
			}
		}
		file_same_folder.sort();
		if(file_same_folder.length > 1)
		{
			let f_index = file_same_folder.indexOf(lastfileopened);
			prev_file = file_same_folder[(f_index - 1 + file_same_folder.length) % file_same_folder.length];
			next_file = file_same_folder[(f_index + 1) % file_same_folder.length];
		}
		
		// top bar
		update_top_bar(
			"File: " + lastfileopened,
			function(){ // back callback
				bottom.style.display = "none";
				if(laststringsearch != null) // return to search result if we came from here
				{
					go_search(project.name, returnpath, laststringsearch);
				}
				else
				{
					go_browse(project.name, returnpath);
				}
			},
			function(){ // help
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
			},
			{
				home:1,
				project:1,
				refresh:1,
				refresh_callback:function(){
					bottom.style.display = "none";
					go_file(project.name, lastfileopened);
				},
				slider:1,
				file_nav:+(prev_file != null),
				file_nav_previous_callback:function(){
					bottom.style.display = "none";
					go_file(project.name, prev_file);
				},
				file_nav_next_callback:function(){
					bottom.style.display = "none";
					go_file(project.name, next_file);
				}
			}
		);
		
		// main part
		fragment = new_page();
		
		let topsection = add_to(fragment, "div", {cls:["title"]});
		topsection.innerHTML = project.name;
		add_to(fragment, "div", {cls:["title", "left"]}).innerHTML = lastfileopened;
		let previous_plugin = null;
		// list file actions
		for(const [key, [plugin_name, icon, value]] of Object.entries(data["actions"]))
		{
			if(previous_plugin != plugin_name)
			{
				add_to(fragment, "div", {cls:["title", "left", "interact-group", "smalltext"], br:false}).innerHTML = plugin_name + " Plugin";
				previous_plugin = plugin_name;
			}
			add_interaction(fragment, '<img src="' + (icon == null ? "assets/images/setting.png" : icon) + '"> ' + value, function() {
				if(window.event.ctrlKey || window.confirm("Use " + value + "?")) // confirmation / shortcut to insta confirm
				{
					post("/api/file_action",
						function() {
							go_file(project.name, lastfileopened);
						},
						function() { // reload the file
							go_browse(project.name, returnpath);
						},
						{name:project.name, path:lastfileopened, version:project.version, key:key}
					);
				}
			});
		}
		add_to(fragment, "div", {cls:["title", "left", "interact-group", "smalltext"], br:false}).innerHTML = "Other Actions";
		// add translate this file button
		add_interaction(fragment, '<img src="assets/images/translate.png"> Translate the File', function() {
			if(window.event.ctrlKey || window.confirm("Translate this file?\nIt can take time.")) // confirmation / shortcut to insta confirm
			{
				set_loading_text("Translating this file, be patient...");
				post("/api/translate_file", update_string_list, function(){
					bottom.style.display = "none";
					go_browse(project.name, returnpath);
				}, {name:project.name, path:lastfileopened, version:project.version});
			}
		});
		
		switch(project.config["files"][lastfileopened]["file_type"])
		{
			case 0: // NORMAL
				break;
			case 1: // ARCHIVE
				add_interaction(fragment, '<img src="assets/images/archive.png"> Access Files contained inside', function() {
					go_browse(project.name, lastfileopened + "/");
				});
				add_to(fragment, "div", {cls:["title", "left", "smalltext"]}).innerText = "This file has been divided into multiple files.";
				break;
			case 2: // VIRTUAL
				add_interaction(fragment, '<img src="assets/images/archive.png"> Open Parent File', function() {
					go_file(project.name, project.config["files"][lastfileopened]["parent"]);
				});
				add_to(fragment, "div", {cls:["title", "left", "smalltext"]}).innerText = "This file is part of a bigger file.";
				break;
			case 3: // VIRTUAL_UNDEFINED
				add_to(fragment, "div", {cls:["title", "left", "smalltext"]}).innerText = "If you see this, something went wrong.";
				break;
			default:
				break;
		};
		
		// list strings
		strtablecache = [];
		for(let i = 0; i < project.string_groups.length; ++i)
		{
			prepareGroupOn(fragment, i);
		}
		add_to(fragment, "div", {cls:["spacer"]});
		add_to(fragment, "div", {cls:["spacer"]});
		add_to(fragment, "div", {cls:["spacer"]});
		update_main(fragment).then(() => {
			// update the string list with the data
			let scrollTo = update_string_list(data);
			// scroll to string (if set)
			if(scrollTo)
				scrollTo.scrollIntoView();
			else
				topsection.scrollIntoView();
		});
	}
	catch(err)
	{
		keypressenabled = false;
		console.error("Exception thrown", err.stack);
		push_popup("An unexpected error occured.");
		bottom.style.display = "none";
		project_menu();
	}
}

function copy_string() // used in index.html
{
	if(navigator.clipboard != undefined)
	{
		navigator.clipboard.writeText(edit_ori.textContent);
		push_popup('Original String has been copied');
	}
	else push_popup('You need to be on a secure origin to use the Copy button');
}
// send and confirm a string change, used in index.html
// trash = whether the trash button got used instead
function cancel_string()
{
	bottom.style.display = "none";
	currentstr.classList.toggle("selected-line", false);
}

// send and confirm a string change, used in index.html
// trash = whether the trash button got used instead
function apply_string(trash = false)
{
	bottom.style.display = "none";
	set_loading_text("Updating...");
	// folder path of file
	const returnpath = project.last_data["path"].includes('/') ? project.last_data["path"].split('/').slice(0, project.last_data["path"].split('/').length-1).join('/')+'/' : "";
	if(trash)
		post("/api/update_string", update_string_list, function(){
			bottom.style.display = "none";
			go_browse(project.name, returnpath);
		}, {name:project.name, version:project.version, path:project.last_data["path"], group:currentstr.group, index:currentstr.string});
	else
		post("/api/update_string", update_string_list, function(){
			bottom.style.display = "none";
			go_browse(project.name, returnpath);
		}, {name:project.name, version:project.version, path:project.last_data["path"], group:currentstr.group, index:currentstr.string, string:edit_tl.value});
	currentstr.classList.toggle("selected-line", false);
}

// update the string list
function update_string_list(data)
{
	let searched = null;
	try
	{
		// update list in memory with received data
		project.strings = data["strings"];
		project.string_groups = data["list"];
		let lcstringsearch = laststringsearch != null ? laststringsearch.toLowerCase() : ""; // last searched string (lowercase)
		// iterate over ALL strings
		for(let i = 0; i < strtablecache.length; ++i)
		{
			const elems = strtablecache[i];
			// retrieve string details
			const s = project.string_groups[elems[0].group][elems[0].string];
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
				const g = project.strings[s[0]];
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
		push_popup("An unexpected error occured.");
		project_menu();
	}
	// return searched, which contains either null OR a string to scroll to
	return searched;
}

// used in index.html
function translate_string()
{
	set_loading_text("Fetching translation...");
	post("/api/translate_string", function(data) {
		set_loading(false);
		if(data["translation"] != null)
		{
			edit_tl.value = data["translation"];
			tl_string_length.innerHTML = edit_tl.value.length;
		}
	}, function() {}, {name:project.name, string:edit_ori.textContent});
}

// base for file browsing via /api/local_path
function local_browse(title, explanation, mode)
{
	try
	{
		// don't update upate_page_location here
		
		filebrowsingmode = mode;
		
		// top bar
		update_top_bar(
			title,
			function(){ // back callback
				switch(filebrowsingmode)
				{
					case 0:
						go_main();
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
			},
			null,
			{
				home:1
			}
		);
	
		// main part
		fragment = new_page();
		add_to(fragment, "div", {cls:["title"]}).innerHTML = explanation;
		add_to(fragment, "div", {cls:["left"], id:"current_path"});
		add_to(fragment, "div", {cls:["left", "title"]}).innerHTML = "Folders";
		add_to(fragment, "div", {id:"folder_container"});
		add_to(fragment, "div", {cls:["left", "title"]}).innerHTML = "Files";
		add_to(fragment, "div", {id:"file_container"});
		update_main(fragment).then(() => {
			post("/api/local_path", update_local_browse, null, {"path":"", "mode":filebrowsingmode});
		});
	}
	catch(err)
	{
		keypressenabled = false;
		console.error("Exception thrown", err.stack);
		push_popup("An unexpected error occured.");
		bottom.style.display = "none";
		project_menu();
	}
}

function update_local_browse(data)
{
	// navigation bar
	let path_parts = data["path"].split("/");
	let cpath = document.getElementById("current_path");
	cpath.innerHTML = "";
	let total_path = path_parts[0];
	for(let i = 0; i < path_parts.length; ++i)
	{
		if(i > 0)
			total_path += "/" + path_parts[i];
		const callback_path = total_path;
		add_to(cpath, "div", {cls:["interact", "text-button"], br:false, onclick:function(){
			post("/api/local_path", update_local_browse, null, {"path":callback_path, "mode":filebrowsingmode});
		}}).innerText = path_parts[i];
	}
	// update folders
	let container = document.getElementById("folder_container");
	container.innerHTML = "";
	for(let i = 0; i < data["folders"].length; ++i)
	{
		const t = data["folders"][i];
		add_interaction(container, t.split("/")[t.split("/").length-1], function(){
			if(t == "..")
			{
				if(data["path"].length == 3 && data["path"].endsWith(":/"))
				{
					// special windows case
					post("/api/local_path", update_local_browse, null, {"path":"::", "mode":filebrowsingmode});
				}
				else
				{
					// parent directory
					post("/api/local_path", update_local_browse, null, {"path":data["path"].split('/').slice(0, data["path"].split('/').length-1).join('/'), "mode":filebrowsingmode});
				}
			}
			else
			{
				post("/api/local_path", update_local_browse, null, {"path":t, "mode":filebrowsingmode});
			}
		});
	}
	
	container = document.getElementById("file_container");
	container.innerHTML = "";
	for(let i = 0; i < data["files"].length; ++i)
	{
		const t = data["files"][i];
		add_interaction(container, t.split("/")[t.split("/").length-1], function(){
			switch(filebrowsingmode)
			{
				case 0:
					post("/api/update_location", project_creation, null, {"path":t});
					break;
				case 1:
					post("/api/update_location", project_menu, null, {"name":project.name, "path":t});
					break;
				case 2:
					post("/api/import", project_menu, null, {name:project.name, path:t});
					break;
				case 3:
					post("/api/import_rpgmtrans", project_menu, null, {name:project.name, path:t});
					break;
				default:
					break;
			}
		});
	}
	
	set_loading(false);
}

// prompt for replacing strings
function replace_page()
{
	try
	{
		// top bar
		update_top_bar(
			"Replace strings",
			function(){ // back callback
				project_menu();
			},
			function(){
				help.innerHTML = "<ul>\
					<li>This will replace all matching content of Translated Strings with your replacement.</li>\
					<li>This is Case sensitive.</li>\
				</ul>";
				help.style.display = "";
			}
		);
	
		// main part
		fragment = new_page();
		add_to(fragment, "div", {cls:["title", "left"]}).innerText = "Replace strings by others (Case Sensitive)";
		add_to(fragment, "div", {cls:["title", "left", "smalltext"]}).innerText = "Only translations are affected";
		
		const input = add_to(fragment, "input", {cls:["input", "smallinput"]});
		input.placeholder = "String to replace";
		const output = add_to(fragment, "input", {cls:["input", "smallinput"]});
		output.placeholder = "Replace by";
		add_to(fragment, "div", {cls:["interact", "text-button"], br:false, onclick:function(){
			if(input.value == "")
			{
				push_popup("The input is empty.");
			}
			else if(window.event.ctrlKey || window.confirm("Replace '" + input.value + "'\nby '" + output.value + "'?"))
			{
				post("/api/replace_strings", null, null, {name:project.name, src:input.value, dst:output.value});
			}
		}}).innerHTML = '<img src="assets/images/copy.png"> Replace';
		update_main(fragment);
	}
	catch(err)
	{
		keypressenabled = false;
		console.error("Exception thrown", err.stack);
		push_popup("An unexpected error occured.");
		bottom.style.display = "none";
		project_menu();
	}
}

// wrappers around API calls
function go_main()
{
	post("/api/main", project_list);
}

function go_new_project(at_path, name)
{
	post("/api/new_project", project_menu, go_main, {path:at_path, name:name});
}

function go_project(name)
{
	post("/api/open_project", project_menu, go_main, {name:name});
}

function go_settings(name = null, onerror_back_to_main = false)
{
	if(name == null)
	{
		post("/api/settings", setting_menu, (onerror_back_to_main ? go_main : null));
	}
	else
	{
		post("/api/settings", setting_menu, (onerror_back_to_main ? go_main : null), {name:name});
	}
}

function go_translator(name = null, onerror_back_to_main = false)
{
	if(name == null)
	{
		post("/api/translator", translator_menu, (onerror_back_to_main ? go_main : null));
	}
	else
	{
		post("/api/translator", translator_menu, (onerror_back_to_main ? go_main : null), {name:name});
	}
}

function go_browse(name, in_path, onerror_back_to_main = false)
{
	post("/api/browse", browse_files, (onerror_back_to_main ? go_main : null), {name:name, path:in_path});
}

function go_search(name, in_path, search, onerror_back_to_main = false)
{
	post("/api/search_string", string_search, (onerror_back_to_main ? go_main : null), {name:name, path:in_path, search:search})
}

function go_patches(name, onerror_back_to_main = false)
{
	post("/api/patches", browse_patches, (onerror_back_to_main ? go_main : null), {name:name});
}

function go_open_patch(name, key, onerror_back_to_main = false)
{
	post("/api/open_patch", edit_patch, (onerror_back_to_main ? go_main : null), {name:name, key:key});
}

function go_backups(name, onerror_back_to_main = false)
{
	post("/api/backups", backup_list, (onerror_back_to_main ? go_main : null), {name:name});
}

function go_file(name, path, onerror_back_to_main = false)
{
	post("/api/file", open_file, (onerror_back_to_main ? go_main : null), {name:name, path:path});
}