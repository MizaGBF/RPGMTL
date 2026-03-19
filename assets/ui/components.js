// base class for the interface components
class Component
{
	constructor(owner)
	{
		this.owner = owner;
	}
}

// hold constants used by the interface
class Constant extends Component
{
	constructor(owner)
	{
		super(owner);
		// fixed parts of the html
		this.const_bar = document.getElementById("top");
		this.const_main = document.getElementById("main");
		this.const_bottom = document.getElementById("bottom");
		this.const_marker_classes = Object.freeze(["", "marker-red", "marker-green", "marker-blue", "marker-pink", "marker-yellow", "marker-cyan"]);
		this.const_cwd_code = "$$__RPGMTL_FORCE_WORKING_DIRECTORY__$$";
	}
	
	get bar()
	{
		return this.const_bar;
	}
	
	get main()
	{
		return this.const_main;
	}
	
	get bottom()
	{
		return this.const_bottom;
	}
	
	get marker_classes()
	{
		return this.const_marker_classes;
	}
	
	get working_directory_code()
	{
		return this.const_cwd_code;
	}
}

// handle the loading animation and text during requests
class Loader extends Component
{
	constructor(owner)
	{
		super(owner);
		this.loader = document.getElementById("loading");
		this.ltext = document.getElementById("loader-text");
		this.animation = document.getElementById("loader-animation");
		this._is_visible = true;
	}
	
	get visible()
	{
		return this._is_visible;
	}
	
	set state(bool)
	{
		this.animation.classList.toggle("loader", bool);
		if(bool)
		{
			this.loader.style.display = "";
			this._is_visible = true;
		}
		else
		{
			this.loader.style.display = "none";
			this._is_visible = false;
		}
	}
	
	set text(content)
	{
		this.ltext.textContent = content;
	}
}

class Top_Bar extends Component
{
	constructor(owner)
	{
		super(owner);
		this._elements = {};
		this._last_options = {};
		this._init();
	}
	
	has(key)
	{
		return (
			key in this._last_options
			&& this._last_options[key] != null
		);
	}
	
	click(key)
	{
		this._elements[key].click();
	}
	
	// update the top bar
	update(
		title,
		back_callback,
		help_text = null,
		additions = {}
	)
	{
		this._elements.title.innerText = title;
		this._elements.back.onclick = back_callback;
		this._set_help(help_text);
		this._set_shutdown(additions.shutdown);
		this._set_home(additions.home);
		this._set_project(additions.project);
		this._set_github(additions.github);
		this._set_refresh(
			additions.refresh,
			additions.refresh_callback
		);
		this._set_slider(additions.slider);
		this._set_file_navigation(
			additions.file_nav,
			additions.file_nav_previous_callback,
			additions.file_nav_next_callback
		);
		this._last_options = additions;
	}
	
	_init()
	{
		let fragment = document.createDocumentFragment();
		this._elements.back = util.add_button(
			fragment,
			"Back",
			null,
			null,
			false
		);
		this._elements.title = util.add_to(
			fragment,
			"div",
			{
				cls:["inline", "text-wrapper"]
			}
		);
		this._elements.spacer = util.add_to(
			fragment,
			"div",
			{
				cls:["barfill"]
			}
		);
		this._elements.help = util.add_button(
			fragment,
			"Help",
			"assets/images/help.png",
			() => {
				this.owner.help.open();
			},
			false
		);
		this.owner.constant.bar.appendChild(fragment);
	}
	
	_set_help(text)
	{
		if(text == null)
		{
			this._elements.help.style.display = "none";
		}
		else
		{
			this._elements.help.style.display = "";
			this.owner.help.text = text;
		}
	}
	
	_set_shutdown(is_shutdown)
	{
		const btn_style = (
			"url(\"assets/images/"
			+ (
				is_shutdown
				? "shutdown"
				: "back"
			)
			+ ".png\")"
		);
		this._elements.back.title = is_shutdown ? "Shutdown" : "Back";
		if(this._elements.back.style.backgroundImage != btn_style)
		{
			this._elements.back.style.backgroundImage = btn_style;
		}
	}
	
	_set_home(flag)
	{
		if(flag)
		{
			if(!this._elements.home)
			{
				this._elements.home = util.add_button(
					null,
					"Project Select Page",
					"assets/images/home.png",
					() => {
						this.owner.edit.close();
						this.owner.routes.main();
					},
					false
				);
				this._elements.back.after(this._elements.home);
			}
		}
		else
		{
			if(this._elements.home)
			{
				if(this._elements.home.parentNode)
				{
					this._elements.home.parentNode
					.removeChild(this._elements.home);
				}
				delete this._elements.home;
			}
		}
	}
	
	_set_project(flag)
	{
		if(flag)
		{
			if(!this._elements.project)
			{
				this._elements.project = util.add_button(
					null,
					"Project Menu",
					"assets/images/project.png",
					() => {
						this.owner.edit.close();
						this.owner.routes.project(
							this.owner.project.name
						);
					},
					false
				);
				if(this._elements.home)
				{
					this._elements.home.after(this._elements.project);
				}
				else
				{
					this._elements.back.after(this._elements.project);
				}
			}
		}
		else
		{
			if(this._elements.project)
			{
				if(this._elements.project.parentNode)
				{
					this._elements.project.parentNode
					.removeChild(this._elements.project);
				}
				delete this._elements.project;
			}
		}
	}
	
	_set_github(flag)
	{
		if(flag)
		{
			if(!this._elements.github)
			{
				this._elements.github = util.add_button(
					null,
					"Github Page",
					"assets/images/github.png",
					() => {
						window.open(
							"https://github.com/MizaGBF/RPGMTL",
							"_blank"
						);
					},
					false
				);
				this._elements.help.before(this._elements.github);
			}
		}
		else
		{
			if(this._elements.github)
			{
				if(this._elements.github.parentNode)
				{
					this._elements.github.parentNode
					.removeChild(this._elements.github);
				}
				delete this._elements.github;
			}
		}
	}
	
	_set_refresh(flag, callback)
	{
		if(flag && callback)
		{
			if(!this._elements.refresh)
			{
				this._elements.refresh = util.add_button(
					null,
					"Refresh",
					"assets/images/update.png",
					callback,
					false
				);
				this._elements.help.before(this._elements.refresh);
			}
			else
			{
				this._elements.refresh.onclick = callback;
			}
		}
		else
		{
			if(this._elements.refresh)
			{
				if(this._elements.refresh.parentNode)
				{
					this._elements.refresh.parentNode
					.removeChild(this._elements.refresh);
				}
				delete this._elements.refresh;
			}
		}
	}
	
	_set_slider(flag)
	{
		if(flag)
		{
			if(!this._elements.slider)
			{
				this._elements.slider = util.add_button(
					null,
					"Slide String Areas",
					"assets/images/tl_slide.png",
					() => {
						this.owner.string_style = (this.owner.string_style + 1) % 5;
						/* Positions
							10% 25% 50% 75% 90%
						*/
						const percents = [10, 25, 50, 75, 90];
						document.documentElement
						.style.setProperty(
							'--ori-width',
							percents[this.owner.string_style] + "%"
						);
						document.documentElement
						.style.setProperty(
							'--tl-width',
							(100 - percents[this.owner.string_style]) + "%"
						);
					},
					false
				);
				if(this._elements.refresh)
				{
					this._elements.refresh.before(this._elements.slider);
				}
				else
				{
					this._elements.help.before(this._elements.slider);
				}
			}
		}
		else
		{
			if(this._elements.slider)
			{
				if(this._elements.slider.parentNode)
				{
					this._elements.slider.parentNode
					.removeChild(this._elements.slider);
				}
				delete this._elements.slider;
			}
		}
	}
	
	_set_file_navigation(flag, back_callback, next_callback)
	{
		if(flag)
		{
			if(!this._elements.next_file)
			{
				this._elements.next_file = util.add_button(
					null,
					"Next File",
					"assets/images/next.png",
					next_callback,
					false
				);
				this._elements.slider.before(this._elements.next_file);
			}
			else
			{
				this._elements.next_file.onclick = next_callback;
			}
			if(!this._elements.prev_file)
			{
				this._elements.prev_file = util.add_button(
					null,
					"Previous File",
					"assets/images/previous.png",
					back_callback,
					false
				);
				this._elements.next_file.before(this._elements.prev_file);
			}
			else
			{
				this._elements.prev_file.onclick = back_callback;
			}
		}
		else
		{
			if(this._elements.next_file)
			{
				if(this._elements.next_file.parentNode)
				{
					this._elements.next_file.parentNode
					.removeChild(this._elements.next_file);
				}
				delete this._elements.next_file;
			}
			if(this._elements.prev_file)
			{
				if(this._elements.prev_file.parentNode)
				{
					this._elements.prev_file.parentNode
					.removeChild(this._elements.prev_file);
				}
				delete this._elements.prev_file;
			}
		}
	}
}

class Edit_Area extends Component
{
	constructor(owner)
	{
		super(owner);
		
		this.original = document.getElementById("edit-ori");
		this.occurence = document.getElementById("edit-times");
		this.translation = document.getElementById("edit-tl");
		this.string_length = document.getElementById("string-length");
		
		this._is_open = false;
		
		this.buttons = {};
		this.buttons.trash = document.getElementById("edit-btn-trash");
		this.buttons.search = document.getElementById("edit-btn-search");
		this.buttons.copy = document.getElementById("edit-btn-copy");
		this.buttons.translate = document.getElementById("edit-btn-translate");
		this.buttons.close = document.getElementById("edit-btn-close");
		this.buttons.save = document.getElementById("edit-btn-save");
	}
	
	open(occurence, original, translation)
	{
		// initialize
		if(occurence > 1)
		{
			this.occurence.textContent = occurence + " occurences of this string in the game";
		}
		else
		{
			this.occurence.textContent = "";
		}
		this.original.textContent = original;
		this.translation.value = translation;
		this.string_length.textContent = translation.length;
		// open
		this._is_open = true;
		this.owner.constant.bottom.style.display = "";
		this.translation.focus();
	}
	
	close()
	{
		this._is_open = false;
		this.owner.constant.bottom.style.display = "none";
	}
	
	is_open()
	{
		return this._is_open;
	}
}

class Project_Info extends Component
{
	constructor(owner)
	{
		super(owner);
		// TOFIX
		//this.path = null;
		this.name = null;
		this.config = null;
		this.version = null;
	}
	
	reset()
	{
		//this.path = null;
		this.name = null;
		this.config = null;
		this.version = null;
	}
}

class Help extends Component
{
	constructor(owner)
	{
		super(owner);
		this._is_open = false;
		this._element = document.getElementById("help");
	}
	
	set text(help_text)
	{
		this._element.innerHTML = help_text;
	}
	
	open()
	{
		this._is_open = true;
		this._element.style.display = "";
	}
	
	close()
	{
		this._is_open = false;
		this._element.style.display = "none";
		this.owner.focus();
	}
	
	is_open()
	{
		return this._is_open;
	}
}

// used for keyboard navigation
class Navigables extends Component
{
	constructor(owner)
	{
		super(owner);
		this._navigables = [];
		this._index = 0;
	}
	
	reset(reset_index = true)
	{
		this._navigables = document.querySelectorAll('[tabindex="0"]');
		if(reset_index);
			this._index = 0;
	}
	
	focus()
	{
		if(this._navigables.length == 0)
		{
			return;
		}
		this._navigables[this._index].focus({preventScroll: true});
	}
	
	update_focus(el)
	{
		for(let i = 0; i < this._navigables.length; ++i)
		{
			if(el == this._navigables[i])
			{
				this._index = i;
				return;
			}
		}
	}
	
	has_any()
	{
		return this._navigables.length > 0;
	}
	
	count()
	{
		return this._navigables.length;
	}
	
	to_string_index(string_count)
	{
		return this._index - (this._navigables.length - string_count);
	}
	
	next()
	{
		this._index = this.next_dry();
		return this._index;
	}
	
	previous()
	{
		this._index = this.previous_dry();
		return this._index;
	}
	
	next_dry()
	{
		return (this._index + 1) % this._navigables.length;
	}
	
	previous_dry()
	{
		return (this._index - 1 + this._navigables.length) % this._navigables.length;
	}
	
	at(idx)
	{
		return this._navigables[idx];
	}
	
	get element()
	{
		return this._navigables[this._index];
	}
	
	get index()
	{
		return this._index;
	}
	
	set index(idx)
	{
		console.assert(idx > 0);
		this._index = idx;
	}
	
	move_down(target)
	{
		if(this._navigables.length > 0)
		{
			this.update_focus(target);
			// grid navigation
			let is_updated = false;
			const elem = this._navigables[this._index];
			if(elem.classList.contains("grid-cell"))
			{
				const focused_rect = elem.getBoundingClientRect();
				let best_candidate = null;
				for(
					let i = this._index + 1;
					i < this._navigables.length;
					++i
				)
				{
					if(!this._navigables[i].classList.contains("grid-cell"))
					{
						best_candidate = i;
						break;
					}
					const rect = this._navigables[i].getBoundingClientRect();
					if(rect.x >= focused_rect.x && rect.y > focused_rect.y)
					{
						best_candidate = i;
						break;
					}
					best_candidate = i;
				}
				if(best_candidate != null)
				{
					this._index = best_candidate;
					is_updated = true;
				}
			}
			// fallback to normal
			if(!is_updated)
			{
				this.next();
			}
			return this._navigables[this._index];
		}
		return null;
	}
	
	move_up(target)
	{
		if(this._navigables.length > 0)
		{
			this.update_focus(target);
			// grid navigation
			let is_updated = false;
			const elem = this._navigables[this._index];
			if(elem.classList.contains("grid-cell"))
			{
				const focused_rect = elem.getBoundingClientRect();
				let best_candidate = null;
				for(
					let i = this._index - 1;
					i >= 0;
					--i
				)
				{
					if(!this._navigables[i].classList.contains("grid-cell"))
					{
						best_candidate = i;
						break;
					}
					const rect = this._navigables[i].getBoundingClientRect();
					if(rect.x >= focused_rect.x && rect.y > focused_rect.y)
					{
						best_candidate = i;
						break;
					}
					best_candidate = i;
				}
				if(best_candidate != null)
				{
					this._index = best_candidate;
					is_updated = true;
				}
			}
			// fallback to normal
			if(!is_updated)
			{
				this.previous();
			}
			return this._navigables[this._index];
		}
		return null;
	}
}

class Tools extends Component
{
	constructor(owner)
	{
		super(owner);
		this._tools = [];
	}
	
	reset()
	{
		this._tools = [];
	}
	
	set(data)
	{
		this._tools = data;
	}
	
	get list()
	{
		return this._tools;
	}
}

class Routing extends Component
{
	constructor(owner)
	{
		super(owner);
	}
	
	load()
	{
		try
		{
			let urlparams = new URLSearchParams(window.location.search);
			let page = urlparams.get("page");
			switch(page)
			{
				case "menu":
				{
					this.project(urlparams.get("name"));
					break;
				}
				case "settings":
				{
					this.settings(
						urlparams.get("name"),
						true
					);
					break;
				}
				case "translator":
				{
					this.translator(
						urlparams.get("name"),
						true
					);
					break;
				}
				case "browse":
				{
					this.browse(
						urlparams.get("name"),
						JSON.parse(util.b64tos(urlparams.get("params"))),
						true
					);
					break;
				}
				case "search_string":
				{
					const p = JSON.parse(
						util.b64tos(urlparams.get("params"))
					);
					this.search(
						urlparams.get("name"),
						p.path,
						p.search,
						(p.casesensitive ?? false),
						(p.contains ?? true),
						true
					);
					break;
				}
				case "patches":
				{
					this.patches(
						urlparams.get("name"),
						true
					);
					break;
				}
				case "open_patch":
				{
					this.open_patch(
						urlparams.get("name"),
						JSON.parse(
							util.b64tos(urlparams.get("params"))
						),
						true
					);
					break;
				}
				case "backups":
				{
					this.backups(
						urlparams.get("name"),
						true
					);
					break;
				}
				case "file":
				{
					this.file(
						urlparams.get("name"),
						JSON.parse(
							util.b64tos(urlparams.get("params"))
						),
						true
					);
					break;
				}
				default:
				{
					this.main();
					break;
				}
			}
		}
		catch(err)
		{
			console.error(err);
			this.main();
		}
	}
	
	redirect_to_project()
	{
		if(
			typeof(this.owner.project.name) == "undefined"
			|| this.owner.project.name == null
		)
		{
			this.main();
		}
		else
		{
			this.project(this.owner.project.name);
		}
	}
	
	main()
	{
		this.owner.post(
			"/api/main",
			(data) => this.owner.project_list(data)
		);
	}

	new_project(at_path, name)
	{
		this.owner.post(
			"/api/new_project",
			() => this.redirect_to_project(),
			() => this.main(),
			{
				path:at_path,
				name:name
			}
		);
	}
	
	project(name)
	{
		this.owner.post(
			"/api/open_project",
			(data) => this.owner.project_menu(data),
			() => this.main(),
			{
				name:name
			}
		);
	}
	
	settings(name = null, onerror_back_to_main = false)
	{
		this.owner.post(
			"/api/settings",
			(data) => this.owner.setting_menu(data),
			(
				onerror_back_to_main
				? () => this.main()
				: null
			),
			{
				name:(
					name == null
					? null
					: name
				)
			}
		);
	}

	translator(name = null, onerror_back_to_main = false)
	{
		this.owner.post(
			"/api/translator",
			(data) => this.owner.translator_menu(data),
			(
				onerror_back_to_main
				? () => this.main()
				: null
			),
			{
				name:(
					name == null
					? null
					: name
				)
			}
		);
	}
	
	browse(name, in_path, onerror_back_to_main = false)
	{
		this.owner.post(
			"/api/browse",
			(data) => this.owner.browse_files(data),
			(
				onerror_back_to_main
				? () => this.main()
				: null
			),
			{
				name:name,
				path:in_path
			}
		);
	}
	
	search(
		name,
		in_path,
		search,
		casesensitive,
		contains,
		onerror_back_to_main = false
	)
	{
		this.owner.post(
			"/api/search_string",
			(data) => this.owner.string_search(data),
			(
				onerror_back_to_main
				? () => this.main()
				: null
			),
			{
				name:name,
				path:in_path,
				search:search,
				case:casesensitive,
				contains:contains
			}
		);
	}
	
	patches(name, onerror_back_to_main = false)
	{
		this.owner.post(
			"/api/patches",
			(data) => this.owner.browse_patches(data),
			(
				onerror_back_to_main
				? () => this.main()
				: null
			),
			{
				name:name
			}
		);
	}
	
	open_patch(name, key, onerror_back_to_main = false)
	{
		this.owner.post(
			"/api/open_patch",
			(data) => this.owner.edit_patch(data),
			(
				onerror_back_to_main
				? () => this.main()
				: null
			),
			{
				name:name,
				key:key
			}
		);
	}

	backups(name, onerror_back_to_main = false)
	{
		this.owner.post(
			"/api/backups",
			(data) => this.owner.backup_list(data),
			(
				onerror_back_to_main
				? () => this.main()
				: null
			),
			{
				name:name
			}
		);
	}

	file(name, path, onerror_back_to_main = false)
	{
		this.owner.post(
			"/api/file",
			(data) => this.owner.open_file(data),
			(
				onerror_back_to_main
				? () => this.main()
				: null
			),
			{
				name:name,
				path:path
			}
		);
	}
}

class Search_Setting extends Component
{
	constructor(owner)
	{
		super(owner);
		this.string = null;
		this.casesensitive = false;
		this.contains = true;
	}
	
	reset()
	{
		this.string = null;
	}
}

class Shortcuts extends Component
{
	constructor(owner)
	{
		super(owner);
	}
	
	keydown(e)
	{
		if(
			this.owner.loader.visible
			|| e.metaKey
		)
		{
			return;
		}
		let all_allowed = util.is_not_using_input(e.target);
		switch(e.key)
		{
			case "Escape":
			{
				this.escape(e, all_allowed);
				break;
			}
			case "Enter":
			{
				this.enter(e, all_allowed);
				break;
			}
			case "F1":
			{
				this.f1(e, all_allowed);
				break;
			}
			case "e":
			case "E":
			{
				this.e(e, all_allowed);
				break;
			}
			case "s":
			case "S":
			{
				this.s(e, all_allowed);
				break;
			}
			case "q":
			case "Q":
			{
				this.q(e, all_allowed);
				break;
			}
			case "d":
			case "D":
			{
				this.d(e, all_allowed);
				break;
			}
			case "l":
			case "L":
			{
				this.l(e, all_allowed);
				break;
			}
			case "k":
			case "K":
			{
				this.k(e, all_allowed);
				break;
			}
			case "h":
			case "H":
			{
				this.h(e, all_allowed);
				break;
			}
			case "p":
			case "P":
			{
				this.p(e, all_allowed);
				break;
			}
			case "r":
			case "R":
			{
				this.r(e, all_allowed);
				break;
			}
			case "m":
			case "M":
			{
				this.m(e, all_allowed);
				break;
			}
			case "b":
			case "B":
			{
				this.b(e, all_allowed);
				break;
			}
			case "o":
			case "O":
			{
				this.o(e, all_allowed);
				break;
			}
			case "i":
			case "I":
			{
				this.i(e, all_allowed);
				break;
			}
			case "u":
			case "U":
			{
				this.u(e, all_allowed);
				break;
			}
			case "y":
			case "Y":
			{
				this.y(e, all_allowed);
				break;
			}
			case "Tab":
			{
				this.tab(e, all_allowed);
				break;
			}
			case "ArrowLeft":
			{
				this.left(e, all_allowed);
				break;
			}
			case "ArrowRight":
			{
				this.right(e, all_allowed);
				break;
			}
			case "ArrowDown":
			{
				this.down(e, all_allowed);
				break;
			}
			case "ArrowUp":
			{
				this.up(e, all_allowed);
				break;
			}
			case " ": // Space
			{
				this.space(e, all_allowed);
				break;
			}
		}
	}
	
	keyup(e)
	{
		if(
			this.owner.loader.visible
			|| e.metaKey
			|| !util.is_not_using_input(e.target)
		)
		{
			return;
		}
		switch(e.code)
		{
			case "PageDown":
			case "End":
			{
				this.pagedown(e);
				break;
			}
			case "PageUp":
			case "Home":
			{
				this.pageup(e);
				break;
			}
		}
	}
	
	escape(e, all_allowed)
	{
		if(!util.check_sp_key(e, 0, 0, 0))
		{
			return;
		}
		// close help
		if(this.owner.help.is_open())
		{
			this.owner.help.close();
			util.stop_event(e);
		}
		else if(this.owner.edit.is_open())
		{
			if(this.owner.nav.has_any()) // not needed, but...
			{
				this.owner.nav.focus();
				util.stop_event(e);
			}
		}
		// back/shutdown button
		else if(all_allowed)
		{
			this.owner.top_bar.click("back");
			util.stop_event(e);
		}
	}
	
	enter(e, all_allowed)
	{
		if(
			!all_allowed
			|| !util.check_sp_key(e, 0, 0, 0)
			|| !this.owner.nav.has_any()
		)
		{
			return;
		}
		this.owner.nav.update_focus(e.target);
		// open string
		if(e.target.classList.contains("string-group"))
		{
			const idx = this.owner.nav.to_string_index(this.owner.strtablecache.length);
			this.owner.open_string(this.owner.strtablecache[idx][0]);
			util.stop_event(e);
		}
		// click element
		else if(e.target.onclick)
		{
			e.target.click();
			util.stop_event(e);
		}
	}
	
	f1(e, all_allowed)
	{
		// toggle help element
		if(!util.check_sp_key(e, 0, 0, 0))
		{
			return;
		}
		if(this.owner.help.is_open())
		{
			this.owner.help.close();
		}
		else
		{
			this.owner.help.open();
			e.target.blur(); // remove focus from target
		}
		util.stop_event(e);
	}
	
	e(e, all_allowed)
	{
		// go to edit area
		if(
			!all_allowed
			|| !util.check_sp_key(e, 0, 0, 1)
			|| !this.owner.edit.is_open()
		)
		{
			return;
		}
		this.owner.edit.translation.focus();
		util.stop_event(e);
	}
	
	s(e, all_allowed)
	{
		// save string
		if(
			!util.check_sp_key(e, 0, 0, 1)
			|| !this.owner.edit.is_open()
		)
		{
			return;
		}
		this.owner.edit.buttons.save.click();
		util.stop_event(e);
	}
	
	q(e, all_allowed)
	{
		// cancel string
		if(
			!util.check_sp_key(e, 0, 0, 1)
			|| !this.owner.edit.is_open()
		)
		{
			return;
		}
		this.owner.edit.buttons.close.click();
		util.stop_event(e);
	}
	
	d(e, all_allowed)
	{
		// trash string
		if(
			!util.check_sp_key(e, 0, 0, 1)
			|| !this.owner.edit.is_open()
		)
		{
			return;
		}
		this.owner.edit.buttons.trash.click();
		util.stop_event(e);
	}
	
	l(e, all_allowed)
	{
		// search string
		if(
			!util.check_sp_key(e, 0, 0, 1)
			|| !this.owner.edit.is_open()
		)
		{
			return;
		}
		this.owner.edit.buttons.search.click();
		util.stop_event(e);
	}
	
	k(e, all_allowed)
	{
		// translate string
		if(
			!util.check_sp_key(e, 0, 0, 1)
			|| !this.owner.edit.is_open()
		)
		{
			return;
		}
		this.owner.edit.buttons.translate.click();
		util.stop_event(e);
	}
	
	h(e, all_allowed)
	{
		// home button
		if(
			!util.check_sp_key(e, 0, 0, 1)
			|| !this.owner.top_bar.has("home")
		)
		{
			return;
		}
		this.owner.top_bar.click("home");
		util.stop_event(e);
	}
	
	p(e, all_allowed)
	{
		// project button
		if(
			!util.check_sp_key(e, 0, 0, 1)
			|| !this.owner.top_bar.has("project")
		)
		{
			return;
		}
		this.owner.top_bar.click("project");
		util.stop_event(e);
	}
	
	r(e, all_allowed)
	{
		// refresh button
		if(
			!util.check_sp_key(e, 0, 0, 1)
			|| !this.owner.top_bar.has("refresh")
		)
		{
			return;
		}
		this.owner.top_bar.click("refresh");
		util.stop_event(e);
	}
	
	m(e, all_allowed)
	{
		// slider button
		if(
			!util.check_sp_key(e, 0, 0, 1)
			|| !this.owner.top_bar.has("slider")
		)
		{
			return;
		}
		this.owner.top_bar.click("slider");
		util.stop_event(e);
	}
	
	b(e, all_allowed)
	{
		// cycle the color
		if(
			!all_allowed
			|| !util.check_sp_key(e, 0, 0, 1)
			|| !e.target.classList.contains("string-group")
		)
		{
			return;
		}
		this.owner.nav.update_focus(e.target);
		const idx = this.owner.nav.to_string_index(this.owner.strtablecache.length);
		this.owner.cycle_marker(this.owner.strtablecache[idx][0]);
		util.stop_event(e);
	}
	
	o(e, all_allowed)
	{
		// copy original
		if(
			all_allowed
			&& util.check_sp_key(e, 0, 0, 1)
			&& e.target.classList.contains("string-group")
		)
		{
			this.owner.nav.update_focus(e.target);
			const idx = this.owner.nav.to_string_index(this.owner.strtablecache.length);
			this.owner.copy_original(this.owner.strtablecache[idx][3]);
			util.stop_event(e);
		}
		// click button
		else if(
			util.check_sp_key(e, 0, 0, 1)
			&& this.owner.edit.is_open()
		)
		{
			this.owner.edit.buttons.copy.click();
			util.stop_event(e);
		}
	}
	
	i(e, all_allowed)
	{
		// copy translation
		if(
			!all_allowed
			|| !util.check_sp_key(e, 0, 0, 1)
			|| !e.target.classList.contains("string-group")
		)
		{
			return;
		}
		this.owner.nav.update_focus(e.target);
		const idx = this.owner.nav.to_string_index(this.owner.strtablecache.length);
		this.owner.copy_translated(this.owner.strtablecache[idx][2]);
		util.stop_event(e);
	}
	
	u(e, all_allowed)
	{
		// unlink string
		if(
			!all_allowed
			|| !util.check_sp_key(e, 0, 0, 1)
			|| !e.target.classList.contains("string-group")
		)
		{
			return;
		}
		this.owner.nav.update_focus(e.target);
		const idx = this.owner.nav.to_string_index(this.owner.strtablecache.length);
		this.owner.unlink_string(this.owner.strtablecache[idx][0]);
		util.stop_event(e);
	}
	
	y(e, all_allowed)
	{
		// disable string
		if(
			!all_allowed
			|| !e.ctrlKey
			|| !e.target.classList.contains("string-group")
		)
		{
			return;
		}
		this.owner.nav.update_focus(e.target);
		const idx = this.owner.nav.to_string_index(this.owner.strtablecache.length);
		if(e.shiftKey && !e.altKey)
		{
			this.owner.multi_disable_string(this.owner.strtablecache[idx][0]);
		}
		else if(!e.shiftKey && e.altKey)
		{
			this.owner.all_disable_string(this.owner.strtablecache[idx][0]);
		}
		else
		{
			this.owner.disable_string(this.owner.strtablecache[idx][0]);
		}
		util.stop_event(e);
	}
	
	tab(e, all_allowed)
	{
		// tab navigation
		if(
			e.ctrlKey
			|| e.altKey
			|| !this.owner.nav.has_any()
		)
		{
			return;
		}
		this.owner.nav.update_focus(e.target);
		if(e.shiftKey)
		{
			this.owner.nav.previous();
		}
		else
		{
			this.owner.nav.next();
		}
		this.owner.focus_and_scroll(this.owner.nav.element);
		util.stop_event(e);
	}
	
	left(e, all_allowed)
	{
		// previous file
		if(
			util.check_sp_key(e, 0, 0, 1)
			&& this.owner.top_bar.has("file_nav_previous_callback")
		)
		{
			this.owner.top_bar.click("prev_file");
			util.stop_event(e);
		}
		// move previous
		else if(
			all_allowed
			&& util.check_sp_key(e, 0, 0, 0)
			&& this.owner.nav.has_any()
		)
		{
			this.owner.nav.update_focus(e.target);
			this.owner.nav.previous();
			this.owner.focus_and_scroll(this.owner.nav.element);
			util.stop_event(e);
		}
	}
	
	right(e, all_allowed)
	{
		// next file
		if(
			util.check_sp_key(e, 0, 0, 1)
			&& this.owner.top_bar.has("file_nav_next_callback")
		)
		{
			this.owner.top_bar.click("next_file");
			util.stop_event(e);
		}
		// move next
		else if(
			all_allowed
			&& util.check_sp_key(e, 0, 0, 0)
			&& this.owner.nav.has_any()
		)
		{
			this.owner.nav.update_focus(e.target);
			this.owner.nav.next();
			this.owner.focus_and_scroll(this.owner.nav.element);
			util.stop_event(e);
		}
	}
	
	down(e, all_allowed)
	{
		// move next/down
		if(
			!all_allowed
			|| !util.check_sp_key(e, 0, 0, 0)
		)
		{
			return;
		}
		const elem = this.owner.nav.move_down(e.target);
		if(elem != null)
		{
			this.owner.focus_and_scroll(elem);
			util.stop_event(e);
		}
	}
	
	up(e, all_allowed)
	{
		// move previous/up
		if(
			!all_allowed
			|| !util.check_sp_key(e, 0, 0, 0)
		)
		{
			return;
		}
		const elem = this.owner.nav.move_up(e.target);
		if(elem != null)
		{
			this.owner.focus_and_scroll(elem);
			util.stop_event(e);
		}
	}
	
	space(e, all_allowed)
	{
		// next untranslated
		// TOFIX
		let params = new URLSearchParams(window.location.search);
		if(
			!params.has("page")
			|| params.get("page") != "file"
		)
		{
			return;
		}
		if(
			all_allowed
			&& e.ctrlKey
			&& !e.altKey
			&& this.owner.nav.has_any()
		)
		{
			let i = this.owner.nav.next_dry();
			while(i != this.owner.nav.index)
			{
				if(this.owner.nav.at(i).classList.contains("string-group"))
				{
					const idx = i - (this.owner.nav.count() - this.owner.strtablecache.length);
					if(
						this.owner.strtablecache[idx][2].classList.contains("disabled") &&
						(
							e.shiftKey ||
							(
								!e.shiftKey &&
								!this.owner.strtablecache[idx][0].classList.contains("disabled")
							)
						)
					)
					{
						this.owner.nav.index = i;
						this.owner.focus_and_scroll(this.owner.nav.element);
						break;
					}
				}
				i = (i + 1) % this.owner.nav.count();
			}
			util.stop_event(e);
		}
		// next local/unlinked
		else if(
			all_allowed
			&& util.check_sp_key(e, 0, 1, 1)
			&& this.owner.nav.has_any()
		)
		{
			let i = this.owner.nav.next_dry();
			while(i != this.owner.nav.index)
			{
				if(this.owner.nav.at(i).classList.contains("unlinked"))
				{
					this.owner.nav.index = i;
					this.owner.focus_and_scroll(this.owner.nav.element);
					return;
				}
				i = (i + 1) % this.owner.nav.count();
			}
			util.stop_event(e);
		}
	}
	
	pagedown(e)
	{
		this.owner.nav.update_focus(e.target);
		if(
			!util.check_sp_key(e, 0, 0, 0)
			|| util.is_element_in_viewport(this.owner.nav.element)
		)
		{
			return;
		}
		for(let i = 0; i < this.owner.nav.count(); ++i)
		{
			if(util.is_element_in_viewport(this.owner.nav.at(i)))
			{
				this.owner.nav.index = i;
				this.owner.focus_and_scroll(this.owner.nav.element);
				break;
			}
		}
		util.stop_event(e);
	}
	
	pageup(e)
	{
		this.owner.nav.update_focus(e.target);
		if(
			!util.check_sp_key(e, 0, 0, 0)
			|| util.is_element_in_viewport(this.owner.nav.element)
		)
		{
			return;
		}
		for(let i = this.owner.nav.count() - 1; i >= 0; --i)
		{
			if(util.is_element_in_viewport(this.owner.nav.at(i)))
			{
				this.owner.nav.index = i;
				this.owner.focus_and_scroll(this.owner.nav.element);
				break;
			}
		}
	}
}
