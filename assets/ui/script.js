// main parts
var bar = null;
var main = null;
var bottom = null;
var top_bar_elems = {}; // contains update_top_bar elements
var edit_btns = {}; // contains button from the edit-tl area from the html
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
var path = null;
var project = {}; // current project
var tools = []; // RPGMTL tools
var tool_params = null;
var currentstr = null;
var strtablecache = [];
var lastfileopened = null;
var search_state = {
	string:null,
	casesensitive:false,
	contains:true
};
var filebrowsingmode = 0;
var navigables = []; // elements with tabindex = 0
var navigable_index = 0;

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
	// edit-tl buttons
	edit_btns.trash = document.getElementById("edit-btn-trash");
	edit_btns.search = document.getElementById("edit-btn-search");
	edit_btns.copy = document.getElementById("edit-btn-copy");
	edit_btns.translate = document.getElementById("edit-btn-translate");
	edit_btns.close = document.getElementById("edit-btn-close");
	edit_btns.save = document.getElementById("edit-btn-save");
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
				go_search(urlparams.get("name"), p.path, p.search, (p.casesensitive ?? false), (p.contains ?? true), true);
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

// close help overlay
function close_help()
{
	help.style.display = "none";
	if(navigables.length > 0)
		navigables[navigable_index].focus({preventScroll: true});
}

// Reset major variables
function clear_variables()
{
	path = null;
	project = {};
	currentstr = null;
	strtablecache = [];
	lastfileopened = null;
	search_state.string = null;
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

// update the navigable index if our focused element is part of our navigable ones
function update_focus(el)
{
	for(let i = 0; i < navigables.length; ++i)
	{
		if(el == navigables[i])
		{
			if(navigable_index != i)
			{
				navigable_index = i;
				return;
			}
		}
	}
}

// return true if user isn't using an input
function is_not_using_input(el)
{
	return !(["TEXTAREA", "INPUT"].includes(el.tagName) || el.classList.contains("input"));
}

// focus element and scroll window if needed
function focus_and_scroll(el)
{
	el.focus({preventScroll: true});
	let rect = el.getBoundingClientRect();
	// top bar element (use hardcoded height for speed)
	if(rect.top <= 50)
	{
		main.scrollBy(0, rect.top - 50);
	}
	// bottom part (if visible)
	else if(bottom.style.display == "")
	{
		let b = bottom.getBoundingClientRect();
		if(rect.bottom >= b.top - 2)
		{
			main.scrollBy(0, rect.bottom - b.top + 2);
		}
	}
	// bottom of viewport
	else if(rect.bottom >= window.innerHeight - 2)
	{
		main.scrollBy(0, rect.bottom - window.innerHeight + 2);
	}
}

// for keyboard shortcut and navigation
document.addEventListener('keydown', function(e)
{
	if(loader.style.display != "none" || e.altKey || e.metaKey)
		return;
	let all_allowed = is_not_using_input(e.target);
	switch(e.key)
	{
		case "Escape":
		{
			if(!e.ctrlKey && !e.shiftKey)
			{
				// close help
				if(help.style.display != "none")
				{
					close_help();
					e.stopPropagation();
					e.preventDefault();
				}
				else if(bottom.style.display != "none")
				{
					if(navigables.length > 0) // not needed, but...
					{
						navigables[navigable_index].focus({preventScroll: true});
						e.stopPropagation();
						e.preventDefault();
					}
				}
				// back/shutdown button
				else if(all_allowed)
				{
					if(top_bar_elems.back && top_bar_elems.back.style.display != "none")
					{
						top_bar_elems.back.click();
						e.stopPropagation();
						e.preventDefault();
					}
				}
			}
			break;
		}
		case "Enter":
		{
			if(!e.ctrlKey && !e.shiftKey && all_allowed && navigables.length > 0)
			{
				update_focus(e.target);
				// open string
				if(e.target.classList.contains("string-group"))
				{
					let idx = navigable_index - (navigables.length - strtablecache.length);
					open_string(strtablecache[idx][0]);
					e.stopPropagation();
					e.preventDefault();
				}
				// click element
				else if(e.target.onclick)
				{
					e.target.click();
					e.stopPropagation();
					e.preventDefault();
				}
			}
			break;
		}
		case "F1":
		{
			// toggle help
			if(!e.ctrlKey && !e.shiftKey && top_bar_elems.help && top_bar_elems.help.style.display != "none")
			{
				if(help.style.display != "none")
				{
					close_help();
					e.stopPropagation();
					e.preventDefault();
				}
				else
				{
					top_bar_elems.help.click();
					e.target.blur();
					e.stopPropagation();
					e.preventDefault();
				}
			}
			break;
		}
		case "e":
		case "E":
		{
			// go to edit area
			if(all_allowed && e.ctrlKey && !e.shiftKey && bottom.style.display != "none")
			{
				edit_tl.focus();
				e.stopPropagation();
				e.preventDefault();
			}
			break;
		}
		case "s":
		case "S":
		{
			// save string
			if(e.ctrlKey && !e.shiftKey && bottom.style.display != "none")
			{
				edit_btns.save.click();
				e.stopPropagation();
				e.preventDefault();
			}
			break;
		}
		case "q":
		case "Q":
		{
			// cancel string
			if(e.ctrlKey && !e.shiftKey && bottom.style.display != "none")
			{
				edit_btns.close.click();
				e.stopPropagation();
				e.preventDefault();
			}
			break;
		}
		case "d":
		case "D":
		{
			// trash string
			if(e.ctrlKey && !e.shiftKey && bottom.style.display != "none")
			{
				edit_btns.trash.click();
				e.stopPropagation();
				e.preventDefault();
			}
			break;
		}
		case "l":
		case "L":
		{
			// search string
			if(e.ctrlKey && !e.shiftKey && bottom.style.display != "none")
			{
				edit_btns.search.click();
				e.stopPropagation();
				e.preventDefault();
			}
			break;
		}
		case "k":
		case "K":
		{
			// translate string
			if(e.ctrlKey && !e.shiftKey && bottom.style.display != "none")
			{
				edit_btns.translate.click();
				e.stopPropagation();
				e.preventDefault();
			}
			break;
		}
		case "h":
		case "H":
		{
			// home button
			if(e.ctrlKey && !e.shiftKey && top_bar_elems.home && top_bar_elems.home.style.display != "none")
			{
				top_bar_elems.home.click();
				e.stopPropagation();
				e.preventDefault();
			}
			break;
		}
		case "p":
		case "P":
		{
			// project button
			if(e.ctrlKey && !e.shiftKey && top_bar_elems.project && top_bar_elems.project.style.display != "none")
			{
				top_bar_elems.project.click();
				e.stopPropagation();
				e.preventDefault();
			}
			break;
		}
		case "r":
		case "R":
		{
			// refresh button
			if(e.ctrlKey && !e.shiftKey && top_bar_elems.refresh && top_bar_elems.refresh.style.display != "none")
			{
				top_bar_elems.refresh.click();
				e.stopPropagation();
				e.preventDefault();
			}
			break;
		}
		case "m":
		case "M":
		{
			// slide button
			if(e.ctrlKey && !e.shiftKey && top_bar_elems.slider && top_bar_elems.slider.style.display != "none")
			{
				top_bar_elems.slider.click();
				e.stopPropagation();
				e.preventDefault();
			}
			break;
		}
		case "o":
		case "O":
		{
			// copy original
			if(all_allowed && e.ctrlKey && !e.shiftKey && e.target.classList.contains("string-group"))
			{
				update_focus(e.target);
				let idx = navigable_index - (navigables.length - strtablecache.length);
				copy_original(strtablecache[idx][3]);
				e.stopPropagation();
				e.preventDefault();
			}
			// click button
			else if(e.ctrlKey && !e.shiftKey && bottom.style.display != "none")
			{
				edit_btns.copy.click();
				e.stopPropagation();
				e.preventDefault();
			}
			break;
		}
		case "i":
		case "I":
		{
			// copy translation
			if(all_allowed && e.ctrlKey && !e.shiftKey && e.target.classList.contains("string-group"))
			{
				update_focus(e.target);
				let idx = navigable_index - (navigables.length - strtablecache.length);
				copy_translated(strtablecache[idx][2]);
				e.stopPropagation();
				e.preventDefault();
			}
			break;
		}
		case "u":
		case "U":
		{
			// unlink string
			if(all_allowed && e.ctrlKey && !e.shiftKey && e.target.classList.contains("string-group"))
			{
				update_focus(e.target);
				let idx = navigable_index - (navigables.length - strtablecache.length);
				unlink_string(strtablecache[idx][0]);
				e.stopPropagation();
				e.preventDefault();
			}
			break;
		}
		case "y":
		case "Y":
		{
			// disable string
			if(all_allowed && e.ctrlKey && e.target.classList.contains("string-group"))
			{
				update_focus(e.target);
				let idx = navigable_index - (navigables.length - strtablecache.length);
				if(e.shiftKey)
				{
					multi_disable_string(strtablecache[idx][0]);
				}
				else
				{
					disable_string(strtablecache[idx][0]);
				}
				e.stopPropagation();
				e.preventDefault();
			}
			break;
		}
		case "Tab":
		{
			// tab navigation
			if(!e.ctrlKey && navigables.length > 0)
			{
				update_focus(e.target);
				if(e.shiftKey)
				{
					navigable_index = (navigable_index - 1 + navigables.length) % navigables.length;
				}
				else
				{
					navigable_index = (navigable_index + 1) % navigables.length;
				}
				focus_and_scroll(navigables[navigable_index]);
				e.stopPropagation();
				e.preventDefault();
			}
			break;
		}
		case "ArrowLeft":
		{
			// previous file
			if(e.ctrlKey && !e.shiftKey && top_bar_elems.prev_file && top_bar_elems.prev_file.style.display != "none")
			{
				top_bar_elems.prev_file.click();
				e.stopPropagation();
				e.preventDefault();
			}
			// move previous
			else if(!e.ctrlKey && !e.shiftKey && all_allowed && navigables.length > 0)
			{
				update_focus(e.target);
				navigable_index = (navigable_index - 1 + navigables.length) % navigables.length;
				focus_and_scroll(navigables[navigable_index]);
				e.stopPropagation();
				e.preventDefault();
			}
			break;
		}
		case "ArrowRight":
		{
			// next file
			if(e.ctrlKey && !e.shiftKey && top_bar_elems.next_file && top_bar_elems.next_file.style.display != "none")
			{
				top_bar_elems.next_file.click();
				e.stopPropagation();
				e.preventDefault();
			}
			// move next
			else if(!e.ctrlKey && !e.shiftKey && all_allowed && navigables.length > 0)
			{
				update_focus(e.target);
				navigable_index = (navigable_index + 1) % navigables.length;
				focus_and_scroll(navigables[navigable_index]);
				e.stopPropagation();
				e.preventDefault();
			}
			break;
		}
		case "ArrowDown":
		{
			// move next/down
			if(!e.ctrlKey && !e.shiftKey && all_allowed && navigables.length > 0)
			{
				update_focus(e.target);
				// grid navigation
				let is_updated = false;
				if(navigables[navigable_index].classList.contains("grid-cell"))
				{
					const focused_rect = navigables[navigable_index].getBoundingClientRect();
					let best_candidate = null;
					let y_axis = focused_rect.y;
					for(let i = navigable_index + 1; i < navigables.length; ++i)
					{
						if(!navigables[i].classList.contains("grid-cell"))
						{
							best_candidate = i;
							break;
						}
						const rect = navigables[i].getBoundingClientRect();
						if(rect.x >= focused_rect.x && rect.y > focused_rect.y)
						{
							best_candidate = i;
							break;
						}
						best_candidate = i;
					}
					if(best_candidate != null)
					{
						navigable_index = best_candidate;
						is_updated = true;
					}
				}
				// fallback to normal
				if(!is_updated)
					navigable_index = (navigable_index + 1) % navigables.length;
				focus_and_scroll(navigables[navigable_index]);
				e.stopPropagation();
				e.preventDefault();
			}
			break;
		}
		case "ArrowUp":
		{
			// move previous/up
			if(!e.ctrlKey && !e.shiftKey && all_allowed && navigables.length > 0)
			{
				update_focus(e.target);
				// grid navigation
				let is_updated = false;
				if(navigables[navigable_index].classList.contains("grid-cell"))
				{
					const focused_rect = navigables[navigable_index].getBoundingClientRect();
					let best_candidate = null;
					let y_axis = focused_rect.y;
					for(let i = navigable_index - 1; i >= 0; --i)
					{
						if(!navigables[i].classList.contains("grid-cell"))
						{
							best_candidate = i;
							break;
						}
						const rect = navigables[i].getBoundingClientRect();
						if(rect.x <= focused_rect.x && rect.y < focused_rect.y)
						{
							best_candidate = i;
							break;
						}
						best_candidate = i;
					}
					if(best_candidate != null)
					{
						navigable_index = best_candidate;
						is_updated = true;
					}
				}
				// fallback to normal
				if(!is_updated)
					navigable_index = (navigable_index - 1 + navigables.length) % navigables.length;
				focus_and_scroll(navigables[navigable_index]);
				e.stopPropagation();
				e.preventDefault();
			}
			break;
		}
		case " ":
		{
			// next untranslated
			if(all_allowed && e.ctrlKey && navigables.length > 0)
			{
				let params = new URLSearchParams(window.location.search)
				if(params.has("page") && params.get("page") == "file")
				{
					let i = (navigable_index + 1) % navigables.length;
					while(i != navigable_index)
					{
						if(navigables[i].classList.contains("string-group"))
						{
							const idx = i - (navigables.length - strtablecache.length);
							if(
								strtablecache[idx][2].classList.contains("disabled") &&
								(
									e.shiftKey ||
									(
										!e.shiftKey &&
										!strtablecache[idx][0].classList.contains("disabled")
									)
								)
							)
							{
								navigable_index = i;
								focus_and_scroll(navigables[navigable_index]);
								break;
							}
						}
						i = (i + 1) % navigables.length;
					}
					e.stopPropagation();
					e.preventDefault();
				}
			}
			break;
		}
	}
});

document.addEventListener('keyup', function(e)
{
	if(loader.style.display != "none" || e.altKey || e.metaKey || !is_not_using_input(e.target))
		return;
	switch(e.code)
	{
		case "PageDown":
		case "End":
		{
			update_focus(e.target);
			if(!e.ctrlKey && !e.shiftKey && navigables.length > 0 && !is_element_in_viewport(navigables[navigable_index]))
			{
				for(let i = 0; i < navigables.length; ++i)
				{
					if(is_element_in_viewport(navigables[i]))
					{
						navigable_index = i;
						focus_and_scroll(navigables[navigable_index]);
						break;
					}
				}
				e.stopPropagation();
				e.preventDefault();
			}
			break;
		}
		case "PageUp":
		case "Home":
		{
			update_focus(e.target);
			if(!e.ctrlKey && !e.shiftKey && navigables.length > 0 && !is_element_in_viewport(navigables[navigable_index]))
			{
				for(let i = navigables.length - 1; i >= 0; --i)
				{
					if(is_element_in_viewport(navigables[i]))
					{
						navigable_index = i;
						focus_and_scroll(navigables[navigable_index]);
						break;
					}
				}
				e.stopPropagation();
				e.preventDefault();
			}
			break;
		}
	}
});

// return true if element is in viewport
function is_element_in_viewport(el)
{
	const rect = el.getBoundingClientRect();
	return (
		rect.top >= 0 &&
		rect.left >= 0 &&
		rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
		rect.right <= (window.innerWidth || document.documentElement.clientWidth)
	);
}

// create and add a new element to a node, and return it
// support various parameters
function add_to(node, tagName, {cls = [], id = null, title = null, onload = null, onclick = null, onerror = null, navigable = false, br = true}={})
{
	let tag = document.createElement(tagName);
	for(let i = 0; i < cls.length; ++i)
		tag.classList.add(cls[i]);
	if(title) tag.title = title;
	if(id) tag.id = id;
	if(onload) tag.onload = onload;
	if(onclick) tag.onclick = onclick;
	if(onerror) tag.onerror = onerror;
	if(navigable) tag.tabIndex = "0";
	if(node) node.appendChild(tag);
	if(br) node.appendChild(document.createElement("br"));
	return tag;
}

function add_button(node, title, img, callback, navigable)
{
	let btn = add_to(node, "div", {cls:["interact", "button"], title:title, onclick:callback, navigable:navigable, br:false});
	btn.style.backgroundPosition = "6px 0px";
	btn.style.backgroundRepeat = "no-repeat";
	if(img != null)
		btn.style.backgroundImage = "url(\"" + img + "\")";
	return btn;
}

function add_interaction(node, innerHTML, callback)
{
	let interaction = add_to(node, "div", {cls:["interact", "text-wrapper"], onclick:callback, navigable:true});
	interaction.innerHTML = innerHTML;
	return interaction;
}

function add_grid_cell(node, innerHTML, callback)
{
	let cell = add_to(node, "div", {cls:["interact", "text-wrapper", "grid-cell"], onclick:callback, navigable:true, br:false});
	cell.innerHTML = innerHTML;
	return cell;
}

function add_tools(node, callback, filter, bookmark) // callback is intended to be either add_interaction or add_grid_cell
{
	for(const tool of tools)
	{
		if(bookmark)
		{
			const btn = add_button(node, "Set", "assets/images/star.png", null, true);
			const tkey = tool[0];
			if((project.config.bookmarked_tools ?? []).includes(tkey))
				btn.classList.toggle("green", true);
			btn.id = tkey;
			btn.onclick = function(){
				post("/api/bookmark_tool", function() {
					btn.classList.toggle("green", project.config.bookmarked_tools.includes(tkey));
					set_loading(false);
				}, null, {name:project.name, tool:tkey, value:!btn.classList.contains("green")});
			}
		}
		if(filter != null && !filter.includes(tool[0]))
			continue;
		let elem = null;
		switch(tool[4].type)
		{
			case 0:
			{
				elem = callback(
					node, '<img src="' + tool[2] + '"> ' + tool[3],
					function()
					{
						if((tool[4].message ?? "") == "" || window.confirm(tool[4].message))
						{
							post("/api/use_tool", null, null, {name:project.name, tool:tool[0], params:{}});
						}
					}
				);
				break;
			}
			case 1:
			{
				elem = callback(
					node, '<img src="' + tool[2] + '"> ' + tool[3],
					function()
					{
						open_tool(tool[0], tool[3], bookmark);
					}
				);
				break;
			}
			default:
			{
				console.warning("Unknown tool type");
				continue;
			}
		}
		if(bookmark)
		{
			elem.classList.toggle("sideinput", true); // reduce width
		}
	}
}

// set the loading element visibility
function set_loading(state)
{
	if(state)
	{
		loaderanim.classList.add("loader");
		loader.style.display = "";
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
				}).catch(
					error => {
						console.error("Invalid JSON received from the server", error.stack);
						process_call({result:"bad", message:"An Internal Server error occured"}, success, failure);
					}
				);
			} catch(err) {
				console.error("Unexpected error", err.stack);
				set_loading_text("An unexpected error occured.<br>" + err.stack + "<br><br>Refresh the page.<br>Make sure to report the bug if the issue continue.");
			}
		}
	).catch(
		error => {
			console.error("Unexpected error", error.stack);
			process_call({result:"bad", message:"An Internal Server error occured"}, success, failure);
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
function update_main(fragment, to_focus = null)
{
	/*
		use requestAnimationFrame to make sure the fragment is properly calculated,
		to avoid weird flicker/wobble from the CSS kicking in
	*/
    return new Promise((resolve, reject) => {
        requestAnimationFrame(() => {
			main.innerHTML = "";
			main.appendChild(fragment);
			navigables = document.querySelectorAll('[tabindex="0"]');
			navigable_index = 0;
			// Set initial focus
			if(to_focus != null)
			{
				to_focus.focus();
				update_focus(to_focus);
			}
			else
			{
				const firstFocusableElement = main.querySelector('[tabindex="0"]');
				if(firstFocusableElement) // Note: placeholder for future keyboard navigation
				{
					firstFocusableElement.focus({preventScroll: true});
				}
				else
				{
					// If no specific focusable element, try focusing the main content area
					main.focus();
				}
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
		if("message" in json && json["message"] != "")
			push_popup(json["message"]);
		if(json["result"] == "ok") // good result
		{
			if("name" in json["data"] && "config" in json["data"]) // check data content (note: data MUST be present)
			{
				// keep project infos up to date
				project.name = json["data"]["name"];
				project.config = json["data"]["config"];
				project.version = json["data"]["config"]["version"];
				if("tools" in json["data"])
				{
					tools = json["data"]["tools"];
				}
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
		top_bar_elems.back = add_button(fragment, "Back", null, null, false);
		top_bar_elems.title = add_to(fragment, "div", {cls:["inline", "text-wrapper"], br:false});
		top_bar_elems.spacer = add_to(fragment, "div", {cls:["barfill"], br:false});
		top_bar_elems.help = add_button(fragment, "Help", "assets/images/help.png", null, false);
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
			}, false);
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
			}, false);
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
			}, false);
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
			top_bar_elems.refresh = add_button(null, "Refresh", "assets/images/update.png", additions.refresh_callback, false);
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
			}, false);
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
			top_bar_elems.next_file = add_button(null, "Next File", "assets/images/next.png", additions.file_nav_next_callback, false);
			top_bar_elems.slider.before(top_bar_elems.next_file);
		}
		else top_bar_elems.next_file.onclick = additions.file_nav_next_callback;
		if(!top_bar_elems.prev_file)
		{
			top_bar_elems.prev_file = add_button(null, "Previous File", "assets/images/previous.png", additions.file_nav_previous_callback, false);
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
				<li>Use the Shutdown button to stop RPGMTL remotely.</li>\
			</ul>\
			\
			Keyboard shortcuts\
			<ul>\
				<li><b>F1</b> for the help.</li>\
				<li><b>Tab/Shit+Tab</b> and various <b>Arrow keys</b> to move around.</li>\
				<li><b>Enter</b> to interact.</li>\
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
	// add buttons
	grid = add_to(fragment, "div", {cls:["grid"]});
	add_grid_cell(grid, '<img src="assets/images/new.png"> New Project', function(){
		local_browse("Create a project", "Select a Game executable.", 0);
	});
	add_grid_cell(grid, '<img src="assets/images/setting.png"> Settings', function(){
		go_settings(null, true);
	});
	add_grid_cell(grid, '<img src="assets/images/translate.png"> Translators', function(){
		go_translator(null, true);
	});
	add_to(fragment, "div", {cls:["title"]}).innerHTML = "Project List";
	if(data["list"].length > 0) // list projects
	{
		grid = add_to(fragment, "div", {cls:["grid"]});
		for(let i = 0; i < data["list"].length; ++i)
		{
			const t = data["list"][i];
			add_grid_cell(grid, data["list"][i], function(){
				go_project(t);
			});
		}
	}
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
					go_project(project.name);
				else
					go_main();
			},
			function(){ // help
				help.innerHTML = "<ul>\
					<li>Some settings might require you to extract your project strings again, be careful to not lose progress.</li>\
					<li><b>Default</b> Settings are your projects defaults.</li>\
					<li><b>Project</b> Settings override <b>Default</b> Settings when modified.</li>\
				</ul>\
				\
				Keyboard shortcuts\
				<ul>\
					<li><b>F1</b> for the help.</li>\
					<li><b>Tab/Shit+Tab</b> and various <b>Arrow keys</b> to move around.</li>\
					<li><b>Enter</b> to interact.</li>\
					<li><b>Escape</b> to go back.</li>\
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
					go_project(project.name);
				}, null, {name:project.name});
			});
		}
		
		let count = 0;
		// go over received setting menu layout
		for(const [file, fsett] of Object.entries(layout))
		{
			fragment.appendChild(document.createElement("br"));
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
					}, true);
					fragment.appendChild(document.createElement("br"));
					if(key in settings)
						elem.classList.toggle("green", settings[key]);
					++count;
				}
				else if(fdata[1] == "display")
				{
					add_to(fragment, "div", {cls:["settingtext"]}).innerHTML = fdata[0];
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
							add_to(fragment, "div", {cls:["input", "smallinput", "inline"], navigable:true, br:false}) :
							add_to(fragment, "input", {cls:["input", "smallinput"], navigable:true, br:false})
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
								case "text":
									val = input.innerText;
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
						else elem.tabIndex = "0";
						
						if(key in settings)
						{
							switch(fdata[1]) // make sure our value is what RPGMTL wants
							{
								case "text":
									input.textContent = settings[key];
									break;
								default:
									input.value = settings[key];
									break;
							}
						}
						++count;
					}
					else // choice selection
					{
						// add select and option elements
						const sel = add_to(fragment, "select", {cls:["input", "smallinput"], navigable:true, br:false});
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
						fragment.appendChild(document.createElement("br"));
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

// Tool functions
function get_tool(tool_key)
{
	for(const t of tools)
	{
		if(t[0] == tool_key)
			return t;
	}
	return null;
}

function open_tool(tool_key, tool_name, from_tool_list)
{
	try
	{
		const tool = get_tool(tool_key);
		// top bar
		update_top_bar(
			"Tool " + tool_name,
			function(){ // back callback
				if(from_tool_list)
				{
					open_tool_list();
				}
				else
				{
					go_project(project.name);
				}
			},
			function(){ // help
				help.innerHTML = (tool[4]["help"] ?? "There is no help for this Tool.");
				help.style.display = "";
			},
			{
				project:from_tool_list,
				home:1
			}
		);
		
		// main part
		fragment = new_page();
		// add tool parameters
		for(const [key, fdata] of Object.entries(tool[4]["params"]))
		{
			if(fdata[1] == "bool")
			{
				add_to(fragment, "div", {cls:["settingtext"], br:false}).innerHTML = fdata[0];
				// add a simple toggle
				const elem = add_button(fragment, "Set", "assets/images/confirm.png", null, true);
				elem.onclick = function(){
					elem.classList.toggle("green");
				}
				elem.id = key;
				if(fdata[2])
				{
					elem.classList.toggle("green", true);
				}
				fragment.appendChild(document.createElement("br"));
			}
			else if(fdata[1] == "display")
			{
				add_to(fragment, "div", {cls:["settingtext"]}).innerHTML = fdata[0];
			}
			else // other text/number types
			{
				add_to(fragment, "div", {cls:["settingtext"]}).innerHTML = fdata[0];
				if(fdata[3] == null) // text input
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
						add_to(fragment, "div", {cls:["input", "smallinput", "inline"], navigable:true, br:false, id:key}) :
						add_to(fragment, "input", {cls:["input", "smallinput"], navigable:true, br:false, id:key})
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
					fragment.appendChild(document.createElement("br"));
					if(fdata[1] == "text")
					{
						input.tabIndex = "0";
						input.textContent = fdata[2];
					}
					else
					{
						input.value = fdata[2];
					}
				}
				else // choice selection
				{
					// add select and option elements
					const sel = add_to(fragment, "select", {cls:["input", "smallinput"], navigable:true, br:false, id:key});
					for(let i = 0; i < fdata[3].length; ++i)
					{
						let opt = add_to(sel, "option");
						opt.value = fdata[3][i];
						opt.textContent = fdata[3][i];
						if(fdata[3][i] == fdata[2])
						{
							opt.selected = "selected";
						}
					}
					fragment.appendChild(document.createElement("br"));
				}
			}
		}
		// confirm button
		add_interaction(fragment, '<img src="assets/images/confirm.png"> Confirm', function(){
			let params = {};
			for(const [key, fdata] of Object.entries(tool[4]["params"]))
			{
				let elem = document.getElementById(key);
				if(fdata[1] == "bool")
				{
					params[key] = elem.classList.contains("green");
				}
				else if(fdata[1] == "text")
				{
					params[key] = elem.textContent;
				}
				else if(fdata[1] == "display")
				{
					// nothing
				}
				else
				{
					params[key] = elem.value;
				}
			}
			post("/api/use_tool", null, null, {name:project.name, tool:tool[0], params:params});
		});
		
		update_main(fragment);
	}
	catch(err)
	{
		console.error("Exception thrown", err.stack);
		push_popup("An unexpected error occured.");
		go_project();
	}
}

function open_tool_list()
{
	try
	{
		// top bar
		update_top_bar(
			"Tool List",
			function(){ // back callback
				go_project(project.name);
			},
			function(){ // help
				help.innerHTML = "You can use a Tool or bookmark it for the project page.";
				help.style.display = "";
			},
			{
				home:1
			}
		);
		
		// main part
		fragment = new_page();
		
		add_tools(fragment, add_interaction, null, true);
		
		update_main(fragment);
	}
	catch(err)
	{
		console.error("Exception thrown", err.stack);
		push_popup("An unexpected error occured.");
		go_project();
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
					go_project(project.name);
				else
					go_main();
			},
			function(){ // help
				help.innerHTML = "<ul>\
					<li>Select the Translator Plugin to use.</li>\
					<li><b>Default</b> Translator is used by default.</li>\
					<li><b>Project</b> Translator override the <b>Default</b> when modified.</li>\
				</ul>\
				\
				Keyboard shortcuts\
				<ul>\
					<li><b>F1</b> for the help.</li>\
					<li><b>Tab/Shit+Tab</b> and various <b>Arrow keys</b> to move around.</li>\
					<li><b>Enter</b> to interact.</li>\
					<li><b>Escape</b> to go back.</li>\
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
		let possibles_text = ["Single Translation", "Batch Translation"];
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
							go_project(project.name);
						}, null, {name:project.name});
					});
				}
				// add text
				add_to(fragment, "div", {cls:["title", "left"]}).innerHTML = possibles_text[t];
				// add select and option elements
				const sel = add_to(fragment, "select", {cls:["input", "smallinput"], navigable:true, br:false});
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
				</ul>\
				\
				Keyboard shortcuts\
				<ul>\
					<li><b>F1</b> for the help.</li>\
					<li><b>Tab/Shit+Tab</b> and various <b>Arrow keys</b> to move around.</li>\
					<li><b>Enter</b> to interact.</li>\
					<li><b>Escape</b> to go back.</li>\
				</ul>";
				help.style.display = "";
			}
		);
		
		// main part
		fragment = new_page();
		add_to(fragment, "div", {cls:["title", "left"]}).innerHTML = "Folder/Project Name";
		
		// project name input element
		let input = add_to(fragment, "input", {cls:["input"], navigable:true});
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
		
		// explanation
		add_to(fragment, "div", {cls:["title", "left"]}).innerHTML = "After confirming, a backup of the game files will be made in this project folder.<br>You'll then have to set your Project Settings and Extract the strings.";
		
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
					<li>Set your <b>Settings before</b> extracting the strings.</li>\
				</ul>\
				<ul>\
					<li><b>Browse Files</b> to browse and translate strings.</li>\
					<li><b>Add a Fix</b> to add Python patches (Check the README for details).</li>\
					<li><b>Batch Translate</b> will use the Batch Translator to translate all uncomplete and non-ignored files.</li>\
				</ul>\
				<ul>\
					<li><b>Update the Game Files</b> if the Game got updated or if you need to re-copy the files.</li>\
					<li><b>Extract the Strings</b> if you need to extract them from Game files.</li>\
					<li><b>Release a Patch</b> to create a copy of Game files with your translated strings. They will be found in the <b>release</b> folder.</li>\
					<li><b>Unload from Memory</b> if you must do modifications on the local files, using external scripts or whatever.</li>\
				</ul>\
				<ul>\
					<li><b>Replace Strings in batch</b> allows you to do batch replacement of case-sensitive strings.</li>\
					<li><b>Backup Control</b> to open the list of backups if you need to revert the project strings data to an earlier state.</li>\
					<li><b>Import RPGMTL Strings</b> to import strings from RPGMTL projects from any version.</li>\
					<li><b>Import RPGMakerTrans v3 Strings</b> to import strings from RPGMakerTrans v3 projects.</li>\
				</ul>\
				\
				Keyboard shortcuts\
				<ul>\
					<li><b>F1</b> for the help.</li>\
					<li><b>Tab/Shit+Tab</b> and various <b>Arrow keys</b> to move around.</li>\
					<li><b>Enter</b> to interact.</li>\
					<li><b>Escape</b> to go back.</li>\
					<li><b>Ctrl+H</b> to go to the home page.</li>\
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
		add_to(fragment, "div", {cls:["title", "left", "smalltext"]}).innerHTML = "Imported from: " + project.config["path"];
		let grid = null;
		// translate options
		if(project.config.version)
		{
			add_to(fragment, "div", {cls:["title", "left"]}).innerHTML = "Translate";
			grid = add_to(fragment, "div", {cls:["grid"]});
			add_grid_cell(grid, '<img src="assets/images/folder.png"> Browse Files', function(){
				go_browse(project.name, "");
			});
			add_grid_cell(grid, '<img src="assets/images/bandaid.png"> Add a Fix', function(){
				go_patches(project.name);
			});
			add_grid_cell(grid, '<img src="assets/images/translate.png"> Batch Translate', function(){
				if(window.event.ctrlKey || window.confirm("Are you sure you wish to translate the whole game?\nIt will be time consuming.\nMake sure your settings are set properly.")) // confirmation / shortcut to insta confirm
				{
					set_loading_text("Translating the whole game, go do something else...");
					post("/api/translate_project", project_menu, project_menu, {name:project.name});
				}
			});
		}
		// settings options
		add_to(fragment, "div", {cls:["title", "left"]}).innerHTML = "Settings";
		grid = add_to(fragment, "div", {cls:["grid"]});
		add_grid_cell(grid, '<img src="assets/images/setting.png"> Project Settings', function(){
			go_settings(project.name);
		});
		add_grid_cell(grid, '<img src="assets/images/translate.png"> Project Translators', function(){
			go_translator(project.name);
		});
		// main actions
		add_to(fragment, "div", {cls:["title", "left"]}).innerHTML = "Actions";
		grid = add_to(fragment, "div", {cls:["grid"]});
		add_grid_cell(grid, '<img src="assets/images/update.png"> Update the Game Files', function(){
			local_browse("Update project files", "Select the Game executable.", 1);
		});
		add_grid_cell(grid, '<img src="assets/images/export.png"> Extract the Strings', function(){
			if(window.event.ctrlKey || window.confirm("Extract the strings?")) // confirmation / shortcut to insta confirm
			{
				set_loading_text("Extracting, be patient...");
				post("/api/extract", project_menu, go_main, {name:project.name});
			}
		});
		if(project.config.version)
		{
			add_grid_cell(grid, '<img src="assets/images/release.png"> Release a Patch', function(){
				set_loading_text("The patch is being generated in the release folder...");
				post("/api/release", project_menu, null, {name:project.name});
			});
		}
		add_grid_cell(grid, '<img src="assets/images/cancel.png"> Unload from Memory', function(){
			post("/api/unload", go_main, null, {name:project.name});
		});
		if(project.config.version)
		{
			grid = add_to(fragment, "div", {cls:["grid"]});
			add_grid_cell(grid, '<img src="assets/images/copy.png"> Replace Strings in batch', function(){
				replace_page();
			});
			add_grid_cell(grid, '<img src="assets/images/copy.png"> Backup Control', function(){
				go_backups(project.name);
			});
			add_grid_cell(grid, '<img src="assets/images/import.png"> Import RPGMTL Strings', function(){
				local_browse("Import RPGMTL", "Select an old RPGMTL strings file.", 2);
			});
			add_grid_cell(grid, '<img src="assets/images/import.png"> Import RPGMakerTrans v3 Strings', function(){
				local_browse("Import RPGMAKERTRANSPATCH", "Select a RPGMAKERTRANSPATCH file.", 3);
			});
			if(tools.length > 0)
			{
				add_to(fragment, "div", {cls:["title", "left"]}).innerHTML = "Tools";
				grid = add_to(fragment, "div", {cls:["grid"]});
				add_tools(grid, add_grid_cell, (project.config.bookmarked_tools ?? []), false);
				add_grid_cell(grid, '<img src="assets/images/star.png"> All Tools', function(){
					open_tool_list();
				});
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

// generic function to add a search bar on top of the browse file page
function addSearchBar(node, bp, defaultVal = null)
{
	// input element
	add_to(node, "div", {cls:["title", "left", "smalltext", "inline"], br:false}).innerText = "Search";
	const input = add_to(node, "div", {cls:["input", "smallinput", "inline"], navigable:true, br:false});
	input.contentEditable = "plaintext-only";
	if(defaultVal != null)
		input.innerText = defaultVal;
	else if(search_state.string != null) // set last string searched if not null
		input.innerText = search_state.string;
	else
		input.innerText = "";
	// add confirm button
	const button = add_button(node, "Search", "assets/images/search.png", function(){
		if(input.innerText != "")
		{
			go_search(project.name, bp, input.innerText, casesensi.classList.contains("green"), !contains.classList.contains("green"));
		}
	}, true);
	node.appendChild(document.createElement("br"));
	// setting buttons
	add_to(node, "div", {cls:["title", "left", "smalltext", "inline"], br:false}).innerText = "Search settings";
	const casesensi = add_button(fragment, "Case Sensitive", "assets/images/search_case.png", function(){
		this.classList.toggle("green");
	}, true);
	if(search_state.casesensitive)
		casesensi.classList.toggle("green", true);
	const contains = add_button(fragment, "Exact Match", "assets/images/search_exact.png", function(){
		this.classList.toggle("green");
	}, true);
	if(!search_state.contains)
		contains.classList.toggle("green", true);
}

// search original button, used in index.html
function search_this()
{
	let urlparams = new URLSearchParams("");
	urlparams.set("page", "search_string");
	urlparams.set("name", project.name);
	urlparams.set("params", stob64(JSON.stringify({
		name:project.name,
		path:project.last_data["path"],
		search:document.getElementById('edit-ori').textContent,
		casesensitive:true,
		contains:false
	})));
	window.open(window.location.pathname + '?' + urlparams.toString(), '_blank').focus(); // open in another tab
}

// open folder /api/browse
function browse_files(data)
{
	try
	{
		search_state.string = null;
		const bp = data["path"];
		upate_page_location("browse", project.name, bp);
		// top bar
		update_top_bar(
			"Path: " + bp,
			function(){ // back callback
				let returnpath = bp.includes('/') ? bp.split('/').slice(0, bp.split('/').length-2).join('/')+'/' : "";
				// returnpath is the path of the parent folder
				if(bp == "") // current folder is the root, so back to menu
					go_project(project.name);
				else
				{
					if(returnpath == '/') returnpath = ''; // if return path is a single slash, set to empty first
					go_browse(project.name, returnpath);
				}
			},
			function(){ // help
				help.innerHTML = "<ul>\
					<li>Ctrl+Click on a file to <b>disable</b> it, it won't be patched during the release process.</li>\
					<li>The string counts and completion percentages update slowly in the background, don't take them for granted.</li>\
				</ul>\
				\
				Keyboard shortcuts\
				<ul>\
					<li><b>F1</b> for the help.</li>\
					<li><b>Tab/Shit+Tab</b> and various <b>Arrow keys</b> to move around.</li>\
					<li><b>Enter</b> to interact.</li>\
					<li><b>Escape</b> to go back.</li>\
					<li><b>Ctrl+H</b> to go to the home page.</li>\
					<li><b>Ctrl+P</b> to go to the project page.</li>\
					<li><b>Ctrl+R</b> to reload.</li>\
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
		
		let first_element = null;
		add_to(fragment, "div", {cls:["title", "left"]}).innerHTML = bp;
		// go over folders
		for(let i = 0; i < data["folders"].length; ++i)
		{
			const t = data["folders"][i];
			let div = add_to(fragment, "div", {cls:["interact"], navigable:true});
			if(first_element == null)
				first_element = div;
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
			let button = add_to(fragment, "div", {cls:cls[+value], br:false, id:"text:"+key, navigable:true, onclick:function(){
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
			if(first_element == null)
				first_element = button;
			// add completion indicator
			let total = project.config["files"][key]["strings"] - project.config["files"][key]["disabled_strings"];
			let count = project.config["files"][key]["translated"];
			let percent = total > 0 ? ", " + (Math.round(10000 * count / total) / 100) + "%)" : ")";
			
			if(count == total) // add complete class if no string left to translate
				button.classList.add("complete");
			button.textContent = key + ' (' + project.config["files"][key]["strings"] + percent; // set text
			if(key == lastfileopened) // if this is the last opened file
				scrollTo = button; // store it
		}
		// add space at the bottom
		add_to(fragment, "div", {cls:["spacer"]});
		// set completion text
		let progress = {
			all:{
				strings:0,
				translated:0,
				disabled:0
			},
			folder:{
				strings:0,
				translated:0,
				disabled:0
			}
		};
		for(const filepath in project.config["files"])
		{
			if(project.config["files"][filepath].ignored)
			{
				progress.all.disabled += project.config["files"][filepath].strings;
				if(filepath.startsWith(bp))
					progress.folder.disabled += project.config["files"][filepath].strings;
			}
			else
			{
				progress.all.disabled += project.config["files"][filepath].disabled_strings;
				progress.all.strings += project.config["files"][filepath].strings - project.config["files"][filepath].disabled_strings;
				progress.all.translated += project.config["files"][filepath].translated;
				if(filepath.startsWith(bp))
				{
					progress.folder.disabled += project.config["files"][filepath].disabled_strings;
					progress.folder.strings += project.config["files"][filepath].strings - project.config["files"][filepath].disabled_strings;
					progress.folder.translated += project.config["files"][filepath].translated;
				}
			}
		}
		let completion_text = "Progress: " + progress.all.strings + " Strings";
		completion_text += progress.all.strings > 0 ? ', ' + (Math.round(10000 * progress.all.translated / progress.all.strings) / 100) + '%' : '';
		if(progress.all.disabled)
			completion_text += " (" + progress.all.disabled + " ignored Strings)";
		if(progress.all.strings != progress.folder.strings)
		{
			completion_text += "<br>Folders: " + progress.folder.strings + " Strings";
			completion_text += progress.folder.strings > 0 ? ', ' + (Math.round(10000 * progress.folder.translated / progress.folder.strings) / 100) + '%' : '';
			if(progress.folder.disabled)
				completion_text += " (" + progress.folder.disabled + " ignored Strings)";
		}
		completion_text += "<br><i><small>(Progress isn't live updated.)</small></i>";
		completion.innerHTML = completion_text;
		
		update_main(fragment).then(() => {
			if(scrollTo != null) // scroll to last opened file
			{
				scrollTo.scrollIntoView();
				scrollTo.focus({preventScroll: true});
				update_focus(scrollTo);
			}
			else if(first_element)
			{
				first_element.focus({preventScroll: true});
				navigable_index = 1;
			}
		});
		lastfileopened = null; // and clear it
	}
	catch(err)
	{
		lastfileopened = null;
		console.error("Exception thrown", err.stack);
		push_popup("An unexpected error occured.");
		go_project(project.name);
	}
}

// search a string /api/search_string
// it copy/paste stuff from the browse function
function string_search(data)
{
	try
	{
		const bp = data["path"];
		search_state.string = data["search"];
		search_state.casesensitive = data["case"];
		search_state.contains = data["contains"];
		upate_page_location("search_string", project.name, {"path":bp, "search":search_state.string, "casesensitive":search_state.casesensitive, "contains":search_state.contains});
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
					<li>Ctrl+Click on a file to <b>disable</b> it, it won't be patched during the release process.</li>\
				</ul>\
				\
				Keyboard shortcuts\
				<ul>\
					<li><b>F1</b> for the help.</li>\
					<li><b>Tab/Shit+Tab</b> and various <b>Arrow keys</b> to move around.</li>\
					<li><b>Enter</b> to interact.</li>\
					<li><b>Escape</b> to go back.</li>\
					<li><b>Ctrl+H</b> to go to the home page.</li>\
					<li><b>Ctrl+P</b> to go to the project page.</li>\
					<li><b>Ctrl+R</b> to reload.</li>\
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
		
		add_to(fragment, "div", {cls:["title", "left"]}).innerHTML = "Results";
		let cls = [
			["interact", "text-wrapper"],
			["interact", "text-wrapper", "disabled"]
		];
		// list files
		let first_element = null;
		for(const [key, value] of Object.entries(data["files"]))
		{
			let button = add_to(fragment, "div", {cls:cls[+value], br:false, id:"text:"+key, navigable:true, onclick:function(){
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
			if(first_element == null)
				first_element = button;
			let total = project.config["files"][key]["strings"] - project.config["files"][key]["disabled_strings"];
			let count = project.config["files"][key]["translated"];
			let percent = total > 0 ? ', ' + (Math.round(10000 * count / total) / 100) + '%)' : ')';
			if(count == total)
				button.classList.add("complete");
			button.innerHTML = key + ' (' + total + " strings" + percent;
		}
		update_main(fragment, first_element);
	}
	catch(err)
	{
		console.error("Exception thrown", err.stack);
		push_popup("An unexpected error occured.");
		go_project(project.name);
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
				go_project(project.name);
			},
			function(){ // help
				help.innerHTML = "<ul>\
					<li>Select an existing patch/fix or create a new one.</li>\
					<li>The patch/fix will be applied on all files whose name contains the patch/fix name.</li>\
					<li>The patch/fix code must be valid <b>Python</b> code, refer to the <b>README</b> for details.</li>\
				</ul>\
				\
				Keyboard shortcuts\
				<ul>\
					<li><b>F1</b> for the help.</li>\
					<li><b>Tab/Shit+Tab</b> and various <b>Arrow keys</b> to move around.</li>\
					<li><b>Enter</b> to interact.</li>\
					<li><b>Escape</b> to go back.</li>\
					<li><b>Ctrl+H</b> to go to the home page.</li>\
					<li><b>Ctrl+P</b> to go to the project page.</li>\
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
		go_project(project.name);
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
					<li>The patch/fix will be applied on all files whose name contains the patch/fix name.</li>\
					<li>The patch/fix code must be valid <b>Python</b> code, refer to the <b>README</b> for details.</li>\
				</ul>\
				\
				Keyboard shortcuts\
				<ul>\
					<li><b>F1</b> for the help.</li>\
					<li><b>Tab/Shit+Tab</b> and various <b>Arrow keys</b> to move around.</li>\
					<li><b>Enter</b> to interact.</li>\
					<li><b>Escape</b> to go back.</li>\
					<li><b>Ctrl+H</b> to go to the home page.</li>\
					<li><b>Ctrl+P</b> to go to the project page.</li>\
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
		// add various input and text elements
		add_to(fragment, "div", {cls:["title"]}).innerHTML = project.name;
		add_to(fragment, "div", {cls:["title", "left"]}).innerHTML = "Filename match";
		add_to(fragment, "input", {cls:["input"], id:"filter", navigable:true}).type = "text";
		add_to(fragment, "div", {cls:["title", "left"]}).innerHTML = "Python Code";
		add_to(fragment, "div", {cls:["input"], id:"fix", navigable:true}).contentEditable = "plaintext-only";
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
		go_project(project.name);
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
				go_project(project.name);
			},
			function(){ // help
				help.innerHTML = "<ul>\
					<li>Select an existing backup to use it.</li>\
					<li>Click on <b>Use</b> to select the backup.</li>\
					<li>Existing strings.json and its backups will be properly kept, while the selected backup will become the new strings.json.</li>\
				</ul>\
				\
				Keyboard shortcuts\
				<ul>\
					<li><b>F1</b> for the help.</li>\
					<li><b>Tab/Shit+Tab</b> and various <b>Arrow keys</b> to move around.</li>\
					<li><b>Enter</b> to interact.</li>\
					<li><b>Escape</b> to go back.</li>\
					<li><b>Ctrl+H</b> to go to the home page.</li>\
					<li><b>Ctrl+P</b> to go to the project page.</li>\
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
		go_project(project.name);
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
		go_project(project.name);
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
		const span = add_to(base, "span", {cls:["interact", "string-group"], navigable:true}); // add container
		span.group = i;
		span.string = j;
		
		let marker = add_to(span, "div", {cls:["marker", "inline"], br:false}); // left marker (modified, plugins...)
		
		let original = add_to(span, "pre", {cls:["title", "inline", "smalltext", "string-area", "original"], br:false}); // original string
		original.group = i;
		original.string = j;
		original.textContent = project.strings[project.string_groups[i][j][0]][0];
		
		let translation = add_to(span, "pre", {cls:["title", "inline", "smalltext", "string-area", "translation"], br:false}); // translated string
		translation.group = i;
		translation.string = j;
		
		strtablecache.push([span, marker, translation, original]); // add to strtablecache
		span.onclick = function() // add string interactions
		{
			if(window.event.ctrlKey && !window.event.shiftKey && !window.event.altKey) // single disable
			{
				disable_string(this);
			}
			else if(window.event.ctrlKey && !window.event.shiftKey && window.event.altKey) // multi disable
			{
				multi_disable_string(this);
			}
			else if(!window.event.ctrlKey && window.event.shiftKey && !window.event.altKey) // unlink
			{
				if(bottom.style.display == "none")
				{
					unlink_string(this);
				}
			}
		};
		original.onclick = function() // add original string copy
		{
			if(!window.event.ctrlKey && !window.event.shiftKey && window.event.altKey)
			{
				copy_original(this);
				update_focus(span);
			}
		};
		translation.onclick = function() // add translated string copy AND open
		{
			if(!window.event.ctrlKey && !window.event.shiftKey)
			{
				if(window.event.altKey)
				{
					copy_translated(this);
				}
				else
				{
					open_string(span);
				}
				update_focus(span);
			}
		};
	}
}

// string clicks:
function disable_string(elem)
{
	set_loading_text("Updating...");
	post("/api/update_string", update_string_list, null, {setting:1, version:project.version, name:project.name, path:project.last_data["path"], group:elem.group, index:elem.string});
	update_focus(elem);
}

function multi_disable_string(elem)
{
	set_loading_text("Updating...");
	post("/api/update_string", update_string_list, null, {setting:2, version:project.version, name:project.name, path:project.last_data["path"], group:elem.group, index:elem.string});
	update_focus(elem);
}

function unlink_string(elem)
{
	set_loading_text("Updating...");
	post("/api/update_string", update_string_list, null, {setting:0, version:project.version, name:project.name, path:project.last_data["path"], group:elem.group, index:elem.string});
	update_focus(elem);
}

function copy_original(elem)
{
	if(navigator.clipboard != undefined)
	{
		navigator.clipboard.writeText(elem.textContent);
		push_popup('The Original has been copied');
	}
	else push_popup('You need to be on a secure origin to copy');
}

function copy_translated(elem)
{
	if(navigator.clipboard != undefined)
	{
		navigator.clipboard.writeText(elem.textContent);
		push_popup('The Translation has been copied');
	}
	else push_popup('You need to be on a secure origin to copy');
}

function open_string(elem)
{
	// string from project data
	let ss = project.string_groups[elem.group][elem.string];
	// update bottom part
	// set occurence count
	const occurence = project.strings[project.string_groups[elem.group][elem.string][0]][2];
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
	currentstr = elem;
	currentstr.classList.toggle("selected-line", true);
}

// open a file content /api/file
function open_file(data)
{
	try
	{
		// init stuff
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
				if(search_state.string != null) // return to search result if we came from here
				{
					go_search(project.name, returnpath, search_state.string, search_state.casesensitive, search_state.contains);
				}
				else
				{
					go_browse(project.name, returnpath);
				}
			},
			function(){ // help
				help.innerHTML = "<ul>\
					<li><b>Ctrl+Click</b> or <b>Ctrl+Y</b> on a line to make it be <b>ignored</b> during the release process.</li>\
					<li><b>Alt+Ctrl+Click</b> or <b>Ctrl+Shift+Y</b> on a line to <b>ignore ALL</b> occurences of this string in this file.</li>\
					<li><b>Shift+Click</b> or <b>Ctrl+U</b> on a line to <b>unlink</b> it, if you need to set it to a translation specific to this part of the file.</li>\
					<li><b>Alt+Click</b> or <b>Ctrl+O</b> on the original string (on the left) to copy it.</li>\
					<li><b>Alt+Click</b> or <b>Ctrl+I</b> on the translated string (on the right) to copy it.</li>\
					<li><b>Click</b> or press <b>Enter</b> on the translated string (on the right) to edit it.</li>\
					<li><b>Ctrl+Space</b> to scroll to the next untranslated <b>enabled</b> string.</li>\
					<li><b>Shift+Ctrl+Space</b> to scroll to the next untranslated string.</li>\
					<li>On top, if available, you'll find <b>Plugin Actions</b> for this file.</li>\
					<li>You'll also find the <b>Translate the File</b> button.</li>\
				</ul>\
				\
				Other shortcuts\
				<ul>\
					<li><b>F1</b> for the help.</li>\
					<li><b>Tab/Shit+Tab</b> and various <b>Arrow keys</b> to move around.</li>\
					<li><b>Enter</b> to interact.</li>\
					<li><b>Escape</b> to go back.</li>\
					<li><b>Ctrl+H</b> to go to the home page.</li>\
					<li><b>Ctrl+P</b> to go to the project page.</li>\
					<li><b>Ctrl+R</b> to reload.</li>\
					<li><b>Ctrl+M</b> to move and slide the string areas.</li>\
					<li><b>Ctrl+Left/Right</b> to go to the previous/next file, if available.</li>\
					<li><b>Ctrl+E</b> to focus the edit area.</li>\
				</ul>\
				\
				Edit shortcuts\
				<ul>\
					<li><b>Escape</b> to go back to normal navigation, during editing.</li>\
					<li><b>Ctrl+S</b> to save and confirm the translation.</li>\
					<li><b>Ctrl+Q</b> to cancel and close the area.</li>\
					<li><b>Ctrl+K</b> to fetch a translation.</li>\
					<li><b>Ctrl+L</b> to search other occurences.</li>\
					<li><b>Ctrl+O</b> to copy the original string, during editing.</li>\
					<li><b>Ctrl+D</b> to delete the translation.</li>\
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
		// add spaces for bottom part to not cover the last elements
		add_to(fragment, "div", {cls:["spacer"]});
		add_to(fragment, "div", {cls:["spacer"]});
		add_to(fragment, "div", {cls:["spacer"]});
		add_to(fragment, "div", {cls:["spacer"]});
		add_to(fragment, "div", {cls:["spacer"]});
		update_main(fragment).then(() => {
			// update the string list with the data
			let scrollTo = update_string_list(data);
			// scroll to string (if set)
			if(scrollTo)
			{
				scrollTo.scrollIntoView();
				scrollTo.focus();
				update_focus(scrollTo);
			}
			else
				topsection.scrollIntoView();
		});
	}
	catch(err)
	{
		console.error("Exception thrown", err.stack);
		push_popup("An unexpected error occured.");
		bottom.style.display = "none";
		go_project(project.name);
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
	if(navigables.length > 0)
	{
		navigables[navigable_index].focus({preventScroll: true});
	}
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
	if(navigables.length > 0)
	{
		navigables[navigable_index].focus({preventScroll: true});
	}
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
		let lcstringsearch = "";
		// last searched string
		if(search_state.string != null)
		{
			if(!search_state.casesensitive)
				lcstringsearch = search_state.string.toLowerCase();
			else
				lcstringsearch = search_state.string;
		}
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
			// if so, store in searched
			if(search_state.string != null && searched == null)
			{
				if(!search_state.casesensitive)
				{
					if(search_state.contains)
					{
						if(elems[2].textContent.toLowerCase().includes(lcstringsearch)
							|| elems[3].textContent.toLowerCase().includes(lcstringsearch)
						)
						{
							searched = elems[0];
						}
					}
					else
					{
						if(elems[2].textContent.toLowerCase() == lcstringsearch
							|| elems[3].textContent.toLowerCase() == lcstringsearch
						)
						{
							searched = elems[0];
						}
					}
				}
				else
				{
					if(search_state.contains)
					{
						if(elems[2].textContent.includes(lcstringsearch)
							|| elems[3].textContent.includes(lcstringsearch)
						)
						{
							searched = elems[0];
						}
					}
					else
					{
						if(elems[2].textContent == lcstringsearch
							|| elems[3].textContent == lcstringsearch
						)
						{
							searched = elems[0];
						}
					}
				}
			}
		}
		set_loading(false);
	}
	catch(err)
	{
		console.error("Exception thrown", err.stack);
		push_popup("An unexpected error occured.");
		go_project(project.name);
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
					case 0: // new project
						go_main();
						break;
					case 1: // update game
					case 2: // import RPGMTL
					case 3: // import RPGMakerTrans
						go_project(project.name);
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
		add_interaction(fragment, "RPGMTL", function(){
			post("/api/local_path", update_local_browse, null, {"path":"$$__RPGMTL_FORCE_WORKING_DIRECTORY__$$", "mode":filebrowsingmode});
		}).classList.add("text-button");
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
		console.error("Exception thrown", err.stack);
		push_popup("An unexpected error occured.");
		bottom.style.display = "none";
		go_project(project.name);
	}
}

function update_local_browse(data)
{
	// navigation bar
	let path_parts = data["path"].split("/");
	// windows driver letter fix
	if(path_parts.length == 2 && path_parts[1] == "" && path_parts[0][1] == ':')
		path_parts.pop();
	// windows root fix
	if(path_parts.length == 1 && path_parts[0] == "")
		path_parts.pop();
	let cpath = document.getElementById("current_path");
	cpath.innerHTML = "";
	let total_path = path_parts[0];
	for(let i = 0; i < path_parts.length; ++i)
	{
		if(i > 0)
			total_path += "/" + path_parts[i];
		const callback_path = total_path;
		add_to(cpath, "div", {cls:["interact", "text-button"], br:false, navigable:true, onclick:function(){
			post("/api/local_path", update_local_browse, null, {"path":callback_path, "mode":filebrowsingmode});
		}}).innerText = path_parts[i];
	}
	// update folders
	let container = document.getElementById("folder_container");
	container.innerHTML = "";
	let first_element = null;
	for(let i = 0; i < data["folders"].length; ++i)
	{
		const t = data["folders"][i];
		const el = add_interaction(container, t.split("/")[t.split("/").length-1], function(){
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
		if(first_element == null)
			first_element = el;
	}
	container = document.getElementById("file_container");
	container.innerHTML = "";
	let files = data["files"].slice();
	// hack to add a "Select this folder button" for game selection
	if(filebrowsingmode <= 1 && files.length == 0)
	{
		files.push(data["path"] + "/Select this Folder");
	}
	
	for(let i = 0; i < files.length; ++i)
	{
		const t = files[i];
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
	if(first_element != null)
		first_element.focus();
	navigables = document.querySelectorAll('[tabindex="0"]');
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
				go_project(project.name);
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
		
		add_to(fragment, "div", {cls:["title", "left", "smalltext"]}).innerText = "String to replace";
		const input = add_to(fragment, "div", {cls:["input", "smallinput"], navigable:true});
		input.contentEditable = "plaintext-only";
		add_to(fragment, "div", {cls:["title", "left", "smalltext"]}).innerText = "Replacement";
		const output = add_to(fragment, "div", {cls:["input", "smallinput"], navigable:true});
		output.contentEditable = "plaintext-only";
		add_to(fragment, "div", {cls:["interact", "text-button"], br:false, navigable:true, onclick:function(){
			if(input.value == "")
			{
				push_popup("The input is empty.");
			}
			else if(window.event.ctrlKey || window.confirm("Replace '" + input.innerText + "'\nby '" + output.innerText + "'?"))
			{
				post("/api/replace_strings", null, null, {name:project.name, src:input.innerText, dst:output.innerText});
			}
		}}).innerHTML = '<img src="assets/images/copy.png"> Replace';
		update_main(fragment);
	}
	catch(err)
	{
		console.error("Exception thrown", err.stack);
		push_popup("An unexpected error occured.");
		bottom.style.display = "none";
		go_project(project.name);
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

function go_search(name, in_path, search, casesensitive, contains, onerror_back_to_main = false)
{
	post("/api/search_string", string_search, (onerror_back_to_main ? go_main : null), {name:name, path:in_path, search:search, case:casesensitive, contains:contains})
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