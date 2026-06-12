// main class
class RPGMTL_Interface
{
	constructor()
	{
		this.constant = new Constant(this);
		this.loader = new Loader(this);
		this.edit = new Edit_Area(this);
		this.routes = new Routing(this);
		this.project = new Project_Info(this);
		this.progress = new Project_Progress(this);
		this.search = new Search_Setting(this);
		this.top_bar = new Top_Bar(this);
		this.help = new Help(this);
		this.nav = new Navigables(this);
		this.tools = new Tools(this);
		this.shortcuts = new Shortcuts(this);
		
		this.string_style = 2;
		this.currentstr = null;
		this.strtablecache = [];
		this.lastfileopened = null;
		this.filebrowsingmode = 0;
	}
	
	init()
	{
		this.init_listeners();
		this.routes.load();
	}
	
	init_listeners()
	{
		document.addEventListener('keydown', (e) => {
			this.shortcuts.keydown(e);
		});
		document.addEventListener('keyup', (e) => {
			this.shortcuts.keyup(e);
		});
	}
	
	// make a POST request
	// About callbacks:
	// success is called on success
	// failure is called on failure
	post(url, success = null, failure = null, payload = {})
	{
		this.loader.state = true;
		fetch(
			url,
			{
				method: "POST", // Specify the HTTP method
				headers: {
						"Content-Type": "application/json;charset=UTF-8"
				},
				body: JSON.stringify(payload)
			}
		).then(
			response => {
				try
				{
					response.json().then((json) => {
						this.process_call(json, success, failure);
					}).catch(
						error => {
							console.error(
								"Invalid JSON received from the server",
								error.stack
							);
							this.process_call(
								{
									result:"bad",
									message:"An Internal Server error occured"
								},
								success,
								failure
							);
						}
					);
				} catch(err) {
					console.error("Unexpected error", err.stack);
					this.loader.text = (
						"An unexpected error occured.<br>"
						+ err.stack
						+ "<br><br>Refresh the page."
						+ "<br>Make sure to report the bug if the issue continue."
					);
				}
			}
		).catch(
			error => {
				console.error("Unexpected error", error.stack);
				this.process_call(
					{
						result:"bad",
						message:"An Internal Server error occured"
					},
					success,
					failure
				);
			}
		);
	}
	
	// generitc function to process the result of requests
	process_call(json, success, failure)
	{
		try
		{
			if("message" in json && json.message != "")
			{
				util.push_popup(json.message);
			}
			if(json.result == "ok") // good result
			{
				// check data content (note: data MUST be present)
				if(
					"name" in json.data
					&& "config" in json.data
				) 
				{
					// keep project infos up to date
					this.project.name = json.data.name;
					this.project.config = json.data.config;
					this.project.version = json.data.config.version;
					if("tools" in json.data)
					{
						this.tools.set(json.data.tools);
					}
				}
				if(success) // call success callback if it exists
				{
					success(json.data);
				}
				else
				{
					this.loader.state = false;
				}
			}
			else
			{
				if(failure) // call failure callback if it exists
				{
					failure(json);
				}
				else
				{
					this.loader.state = false;
				}
			}
			// reset loading text
			this.loader.text = "Waiting RPGMTL response...";
		}
		catch(err)
		{
			console.error("Exception thrown", err.stack);
			this.loader.text = (
				"An unexpected error occured.<br>"
				+ err.stack
				+ "<br><br>Refresh the page."
				+ "<br>Make sure to report the bug if the issue continue."
			);
		}
	}
	
	clear()
	{
		this.project.reset();
		this.search.reset();
		this.currentstr = null;
		this.strtablecache = [];
		this.lastfileopened = null;
		this.filebrowsingmode = 0;
	}
	
	// wrapper
	focus()
	{
		this.nav.focus();
	}
	
	// callback is intended to be either add_interaction or add_grid_cell
	add_tools(node, callback, filter, bookmark)
	{
		for(const tool of this.tools.list)
		{
			if(bookmark)
			{
				const btn = util.add_button(
					node,
					"Set",
					"assets/images/star.png",
					null,
					true
				);
				const tkey = tool[0];
				if((this.project.config.bookmarked_tools ?? []).includes(tkey))
				{
					btn.classList.toggle("green", true);
				}
				btn.id = tkey;
				btn.onclick = () => {
					this.post(
						"/api/bookmark_tool",
						() => {
							btn.classList.toggle(
								"green",
								this.project.config.bookmarked_tools.includes(tkey)
							);
							this.loader.state = false;
						},
						null,
						{
							name:this.project.name,
							tool:tkey,
							value:!btn.classList.contains("green")
						}
					);
				};
			}
			if(filter != null && !filter.includes(tool[0]))
			{
				continue;
			}
			let elem = null;
			switch(tool[4].type)
			{
				case 0:
				{
					elem = callback(
						node,
						'<img src="' + tool[2] + '"> ' + tool[3],
						() => {
							if(
								(tool[4].message ?? "") == ""
								|| window.confirm(tool[4].message)
							)
							{
								this.post(
									"/api/use_tool",
									null,
									null,
									{
										name:this.project.name,
										tool:tool[0],
										params:{}
									}
								);
							}
						}
					);
					break;
				}
				case 1:
				{
					elem = callback(
						node,
						'<img src="' + tool[2] + '"> ' + tool[3],
						() => {
							this.open_tool(tool[0], tool[3], bookmark);
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
	
	new_page()
	{
		this.loader.state = false;
		return document.createDocumentFragment();
	}
	
	update_main(fragment, to_focus = null)
	{
		/*
			use requestAnimationFrame to make sure the fragment is properly calculated,
			to avoid weird flicker/wobble from the CSS kicking in
		*/
		return new Promise((resolve, reject) => {
			requestAnimationFrame(() => {
				const current_title = this.constant.main.firstElementChild;
				const new_title = fragment.firstElementChild;

				if(current_title && new_title && current_title.isEqualNode(new_title))
				{
					fragment.removeChild(new_title);
					while(this.constant.main.childNodes.length > 1)
					{
						this.constant.main.removeChild(this.constant.main.lastChild);
					}
					this.constant.main.appendChild(fragment);
				}
				else
				{
					this.constant.main.innerHTML = '';
					this.constant.main.appendChild(fragment);
				}
				
				/*this.constant.main.innerHTML = "";
				this.constant.main.appendChild(fragment);*/
				this.nav.reset();
				// Set initial focus
				if(to_focus != null)
				{
					to_focus.focus();
					this.nav.update_focus(to_focus);
				}
				else
				{
					const firstFocusableElement = this.constant.main.querySelector('[tabindex="0"]');
					if(firstFocusableElement) // Note: placeholder for future keyboard navigation
					{
						firstFocusableElement.focus({preventScroll: false});
					}
					else
					{
						// If no specific focusable element, try focusing the main content area
						this.constant.main.focus();
					}
				}
				resolve(); 
			});
		});
	}
	
	// handle result of /api/main
	project_list(data)
	{
		util.update_page_location(null, null, null);
		this.clear(); // in case we got here from an error
		
		// top bar
		this.top_bar.update(
			"RPGMTL v" + data.verstring,
			(e) => { // back callback
				if(
					e.ctrlKey
					|| window.confirm("Shutdown RPGMTL?\nEverything will be saved.")
				)
				{
					this.post(
						"/api/shutdown",
						() => {
							this.constant.bar.innerHTML = "";
							let fragment = this.new_page();
							util.add_label(
								fragment,
								"RPGMTL has been shutdown"
							);
							this.update_main(fragment);
						}
					);
				}
			},
			"<ul>\
				<li>Load an existing <b>Project</b> or create a new one.</li>\
				<li>Use the Shutdown button to stop RPGMTL remotely.</li>\
			</ul>\
			\
			Keyboard shortcuts\
			<ul>\
				<li><b>F1</b> for the help.</li>\
				<li><b>Tab/Shit+Tab</b> and various <b>Arrow keys</b> to move around.</li>\
				<li><b>Enter</b> to interact.</li>\
			</ul>",
			{
				shutdown:1,
				github:1
			}
		);
		
		// main part
		let fragment = this.new_page();
		// title
		util.add_to(
			fragment,
			"div",
			{
				cls:["project-title"],
				innerHTML:'<img src="assets/ui/favicon.svg" class="project-icon-banner" onerror="this.remove();"><div class="rpgmtl-title">RPGMTL<br><small>v' + data.verstring + '</small></div>'
			}
		)
		// add buttons
		let grid = util.add_to(
			fragment,
			"div",
			{
				cls:["grid"],
				br:true
			}
		);
		util.add_grid_cell(grid, '<img src="assets/images/new.png"> New Project', () => {
			this.local_browse("Create a project", "Select a Game executable.", 0);
		});
		util.add_grid_cell(grid, '<img src="assets/images/setting.png"> Settings', () => {
			this.routes.settings(null, true);
		});
		util.add_grid_cell(grid, '<img src="assets/images/translate.png"> Translators', () => {
			this.routes.translator(null, true);
		});
		util.add_label(
			fragment,
			"Project List"
		);
		if(data.list.length > 0) // list projects
		{
			grid = util.add_to(
				fragment,
				"div",
				{
					cls:["grid"],
					br:true
				}
			);
			for(let i = 0; i < data.list.length; ++i)
			{
				const t = data.list[i];
				util.add_grid_cell(
					grid,
					util.project_name_add_icon(data.list[i]),
					() => {
						this.routes.project(t);
					}
				);
			}
		}
		// quick links
		if(data.history.length > 0) // list last browsed Files
		{
			util.add_label(
				fragment,
				"Last Accessed Files",
				["left"]
			);
			for(let i = 0; i < data.history.length; ++i)
			{
				const c_entry = data.history[i];
				util.add_interaction(
					fragment,
					util.project_name_add_icon(c_entry[0]) + ": " + c_entry[1],
					() => {
						this.routes.file(c_entry[0], c_entry[1], true);
					}
				);
			}
		}
		this.update_main(fragment);
	}

	// function to create a reset button for a specific setting
	setting_menu_individual_reset(node, relevant_node, setting_key)
	{
		util.add_button(node, "Reset", "assets/images/update.png", () => {
				if(window.confirm("Are you sure you want to reset this setting?"))
				{
					this.post(
						"/api/update_settings",
						(data) => {
							util.push_popup("The setting has been reset.");
							this.loader.state = false;
							if(setting_key in data.settings)
							{
								switch(relevant_node.tagName)
								{
									case "DIV":
									{
										if(relevant_node.classList.contains("button"))
										{
											relevant_node.classList.toggle("green", data.settings[setting_key]);
										}
										else if(relevant_node.classList.contains("settinginput"))
										{
											relevant_node.innerText = data.settings[setting_key];
										}
										break;
									}
									case "INPUT":
									case "SELECT":
									{
										relevant_node.value = data.settings[setting_key];
										break;
									}
								}
							}
							relevant_node.classList.toggle(
								"settingmodifiedborder",
								data.modified_default.includes(setting_key)
							);
						},
						null,
						{name:this.project.name, key:setting_key}
					);
				}
			},
			true
		);
	}

	// display settings for /api/settings
	setting_menu(data)
	{
		try
		{
			const is_project = "config" in data;
			
			util.update_page_location("settings", (is_project ? this.project.name : null), null);
			
			// top bar
			this.top_bar.update(
				(is_project ? this.project.name + " Settings" : "Default Settings"),
				() => { // back callback
					if(is_project)
						this.routes.project(this.project.name);
					else
						this.routes.main();
				},
				"<ul>\
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
				</ul>",
				{
					home:is_project
				}
			);
			
			// main part
			let fragment = this.new_page();
			const layout = data.layout;
			const settings = data.settings;
			const descriptions = data.descriptions;
			const modified_default = data.modified_default;
			
			if(is_project) // add button to reset settings of THIS project
			{
				util.add_project_title(
					fragment,
					this.project.name
				);
				util.add_interaction(
					fragment,
					'<img src="assets/images/trash.png"> Reset All Settings to RPGMTL Default',
					() => {
						this.post(
							"/api/update_settings",
							() => {
								util.push_popup("The Project Settings have been reset to the global settings.");
								this.routes.settings(this.project.name);
							},
							null,
							{
								name:this.project.name
							}
						);
					}
				);
			}
			
			let count = 0;
			// go over received setting menu layout
			for(const [file, fsett] of Object.entries(layout))
			{
				fragment.appendChild(document.createElement("br"));
				// add plugin name
				util.add_label(
					fragment,
					file + " Plugin settings",
					["left"]
				);
				// and description if it exists
				if(file in descriptions && descriptions[file] != "")
				{
					util.add_to(
						fragment,
						"div",
						{
							cls:["left", "interact-group", "smalltext"],
							innerText:descriptions[file],
							br:true
						}
					);
				}
				// go over options
				for(const [key, fdata] of Object.entries(fsett))
				{
					if(fdata[1] == "bool")
					{
						util.add_to(
							fragment,
							"div",
							{
								cls:["settingtext"],
								innerHTML:fdata[0]
							}
						);
						// add a simple toggle
						const elem = util.add_button(
							fragment,
							"Set",
							"assets/images/confirm.png",
							() => {
								let callback = (result_data) => {
									util.push_popup("The setting has been updated.");
									this.loader.state = false;
									if(key in result_data.settings)
										elem.classList.toggle("green", result_data.settings[key]);
									elem.classList.toggle("settingmodifiedborder", result_data.modified_default.includes(key));
								};
								if(is_project)
								{
									this.post(
										"/api/update_settings",
										callback,
										null,
										{
											name:this.project.name,
											key:key,
											value:!elem.classList.contains("green")
										}
									);
								}
								else
								{
									this.post(
										"/api/update_settings",
										callback,
										null,
										{
											key:key,
											value:!elem.classList.contains("green")
										}
									);
								}
							},
							true
						);
						elem.classList.toggle("settingmodifiedborder", modified_default.includes(key));
						if(is_project)
						{
							this.setting_menu_individual_reset(fragment, elem, key);
						}
						fragment.appendChild(document.createElement("br"));
						if(key in settings)
						{
							elem.classList.toggle("green", settings[key]);
						}
						++count;
					}
					else if(fdata[1] == "display")
					{
						util.add_to(
							fragment,
							"div",
							{
								cls:["settingtext"],
								innerHTML:fdata[0],
								br:true
							}
						);
						++count;
					}
					else // other text/number types
					{
						util.add_to(
							fragment,
							"div",
							{
								cls:["settingtext"],
								innerHTML:fdata[0],
								br:true
							}
						);
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
								fdata[1] == "text"
								? util.add_to(
										fragment,
										"div",
										{
											cls:["input", "settinginput", "inline"],
											navigable:true
										}
									)
								: util.add_to(
									fragment,
									"input",
									{
										cls:["input", "settinginput"],
										navigable:true
									}
								)
							);
							input.classList.toggle("settingmodifiedborder", modified_default.includes(key));
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
							const elem = util.add_button(
								fragment,
								"Set",
								"assets/images/confirm.png",
								() => {
									let val = "";
									switch(fdata[1]) // make sure our value is what RPGMTL wants
									{
										case "num":
											if(isNaN(input.value) || isNaN(parseFloat(input.value)))
											{
												util.push_popup("The value isn't a valid number.");
												return;
											}
											val = Math.floor(parseFloat(input.value));
											break;
										case "text":
											val = input.innerText;
											break;
										default:
											val = input.value;
											break;
									}
									let callback = (result_data) => {
										util.push_popup("The setting has been updated.");
										this.loader.state = false;
										if(key in result_data.settings)
											input.value = result_data.settings[key];
										input.classList.toggle("settingmodifiedborder", result_data.modified_default.includes(key));
									};
									if(is_project)
									{
										this.post(
											"/api/update_settings",
											callback,
											null,
											{
												name:this.project.name,
												key:key,
												value:val
											}
										);
									}
									else
									{
										this.post(
											"/api/update_settings",
											callback,
											null,
											{
												key:key,
												value:val
											}
										);
									}
								}
							);
							if(is_project)
							{
								this.setting_menu_individual_reset(fragment, input, key);
							}
							fragment.appendChild(document.createElement("br"));
							if(fdata[1] != "text")
							{
								// add listener to detect keypress
								input.addEventListener('keypress', (event) => {
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
							const sel = util.add_select(
								fragment,
								fdata[2],
								["settinginput"]
							);
							sel.classList.toggle(
								"settingmodifiedborder",
								modified_default.includes(key)
							);
							// and confirmation button
							const elem = util.add_button(fragment, "Set", "assets/images/confirm.png", () => {
								let callback = (result_data) => {
									util.push_popup("The setting has been updated.");
									this.loader.state = false;
									if(key in result_data.settings)
										sel.value = result_data.settings[key];
									sel.classList.toggle("settingmodifiedborder", result_data.modified_default.includes(key));
								};
								if(is_project)
								{
									this.post(
										"/api/update_settings",
										callback,
										null,
										{
											name:this.project.name,
											key:key,
											value:sel.value
										}
									);
								}
								else
								{
									this.post(
										"/api/update_settings",
										callback,
										null,
										{
											key:key,
											value:sel.value
										}
									);
								}
							});
							if(is_project)
							{
								this.setting_menu_individual_reset(fragment, sel, key);
							}
							fragment.appendChild(document.createElement("br"));
							if(key in settings)
							{
								sel.value = settings[key];
							}
							++count;
						}
					}
				}
			}
			if(count == 0)
			{
				util.add_label(
					fragment,
					"No settings available for your Plugins",
					["left"]
				);
			}
			this.update_main(fragment);
		}
		catch(err)
		{
			console.error("Exception thrown", err.stack);
			util.push_popup("An unexpected error occured.");
			this.routes.main();
		}
	}

	// Tool functions
	get_tool(tool_key)
	{
		for(const t of this.tools.list)
		{
			if(t[0] == tool_key)
			{
				return t;
			}
		}
		return null;
	}

	open_tool(tool_key, tool_name, from_tool_list)
	{
		try
		{
			const tool = this.get_tool(tool_key);
			// top bar
			this.top_bar.update(
				"Tool " + tool_name,
				() => { // back callback
					if(from_tool_list)
					{
						this.open_tool_list();
					}
					else
					{
						this.routes.project(this.project.name);
					}
				},
				(
					tool[4].help
					?? "There is no help for this Tool."
				),
				{
					project:from_tool_list,
					home:1
				}
			);
			
			// main part
			let fragment = this.new_page();
			util.add_project_title(
				fragment,
				this.project.name
			);
			// add tool parameters
			for(const [key, fdata] of Object.entries(tool[4].params))
			{
				if(fdata[1] == "bool")
				{
					util.add_to(
						fragment,
						"div",
						{
							cls:["settingtext"],
							innerHTML:fdata[0]
						}
					);
					// add a simple toggle
					const elem = util.add_button(
						fragment,
						"Set",
						"assets/images/confirm.png",
						null,
						true
					);
					elem.onclick = () => {
						elem.classList.toggle("green");
					};
					elem.id = key;
					if(fdata[2])
					{
						elem.classList.toggle("green", true);
					}
					fragment.appendChild(document.createElement("br"));
				}
				else if(fdata[1] == "display")
				{
					util.add_to(
						fragment,
						"div",
						{
							cls:["settingtext"],
							innerHTML:fdata[0],
							br:true
						}
					);
				}
				else // other text/number types
				{
					util.add_to(
						fragment,
						"div",
						{
							cls:["settingtext"],
							innerHTML:fdata[0],
							br:true
						}
					);
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
							fdata[1] == "text"
							? util.add_to(
								fragment,
								"div",
								{
									cls:["input", "smallinput", "inline"],
									navigable:true,
									id:key
								}
							)
							: util.add_to(
								fragment,
								"input",
								{
									cls:["input", "smallinput"],
									navigable:true,
									id:key
								}
							)
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
						const sel = util.add_select(
							fragment,
							fdata[3],
							["smallinput"],
							fdata[2]
						);
						sel.id = key;
						util.add_to(fragment, "br");
					}
				}
			}
			// confirm button
			util.add_interaction(fragment, '<img src="assets/images/confirm.png"> Confirm', () => {
				let params = {};
				for(const [key, fdata] of Object.entries(tool[4].params))
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
				this.post(
					"/api/use_tool",
					null,
					null,
					{
						name:this.project.name,
						tool:tool[0],
						params:params
					}
				);
			});
			this.update_main(fragment);
		}
		catch(err)
		{
			console.error("Exception thrown", err.stack);
			util.push_popup("An unexpected error occured.");
			this.routes.project(this.project.name);
		}
	}

	open_tool_list()
	{
		try
		{
			// top bar
			this.top_bar.update(
				"Tool List",
				() => { // back callback
					this.routes.project(this.project.name);
				},
				"You can use a Tool or bookmark it for the project page.",
				{
					home:1
				}
			);
			
			// main part
			let fragment = this.new_page();
			util.add_project_title(
				fragment,
				this.project.name
			);
			this.add_tools(
				fragment,
				util.add_interaction,
				null,
				true
			);
			this.update_main(fragment);
		}
		catch(err)
		{
			console.error("Exception thrown", err.stack);
			util.push_popup("An unexpected error occured.");
			this.routes.project(this.project.name);
		}
	}

	open_knowledge()
	{
		try
		{
			// top bar
			this.top_bar.update(
				"Knowledge Base",
				() => { // back callback
					this.routes.project(this.project.name);
				},
				"Consult or edit the Knowledge Base for AI translations",
				{
					home:1
				}
			);
			
			// main part
			let fragment = this.new_page();
			util.add_project_title(
				fragment,
				this.project.name
			);
			util.add_label(
				fragment,
				"Knowledge Base"
			);
			util.add_label(
				fragment,
				"Entry",
				["left", "smalltext", "inline"]
			);
			const selection = util.add_select(
				fragment,
				[],
				["searchinput", "inline"]
			);
			selection.id = "base-select";
			let opt = util.add_to(
				selection,
				"option"
			);
			opt.value = -1;
			opt.selected = true;
			opt.disabled = true;
			opt.textContent = "Select an entry";
			for(let i = 0; i < this.project.config.ai_knowledge_base.length; ++i)
			{
				opt = util.add_to(
					selection,
					"option",
					{
						value:i,
						textContent:(
							this.project.config.ai_knowledge_base[i].original
							+ " / "
							+ this.project.config.ai_knowledge_base[i].translation
						)
					}
				);
			}
			const selected = util.add_label(
				fragment,
				"None selected",
				["left"]
			);
			selected.id = "base-selected";
			selected.original_string = null;
			util.add_label(
				fragment,
				"Original",
				["left", "smalltext"]
			);
			const base_ori = util.add_to(
				fragment,
				"div",
				{
					cls:["input", "searchinput", "inline"],
					id:"base-ori",
					navigable:true
				}
			);
			base_ori.contentEditable = "plaintext-only";
			util.add_label(
				fragment,
				"Translation",
				["left", "smalltext"]
			);
			const base_tl = util.add_to(
				fragment,
				"div",
				{
					cls:["input", "searchinput", "inline"],
					id:"base-tl",
					navigable:true
				}
			);
			base_tl.contentEditable = "plaintext-only";
			util.add_label(
				fragment,
				"Note",
				["left", "smalltext"]
			);
			const base_note = util.add_to(
				fragment,
				"div",
				{
					cls:["input", "searchinput", "inline"],
					id:"base-note",
					navigable:true
				}
			);
			base_note.contentEditable = "plaintext-only";
			util.add_label(
				fragment,
				"Last seen (# of Translation ago)",
				["left", "smalltext"]
			);
			const base_seen = util.add_to(
				fragment,
				"input",
				{
					cls:["input", "searchinput", "inline"],
					id:"base-seen",
					navigable:true
				}
			);
			base_seen.value = "0";
			util.add_label(
				fragment,
				"# of Recent occurences",
				["left", "smalltext"]
			);
			const base_occu = util.add_to(
				fragment,
				"input",
				{
					cls:["input", "searchinput", "inline"],
					id:"base-occu",
					navigable:true
				}
			);
			base_occu.value = "0";
			let grid = util.add_to(
				fragment,
				"div",
				{
					cls:["grid"],
					br:true
				}
			);
			util.add_grid_cell(grid, '<img src="assets/images/new.png"> New', () => {
				selected.innerText = "None selected";
				selected.original_string = null;
				base_ori.textContent = "";
				base_tl.textContent = "";
				base_note.textContent = "";
				base_seen.value = "0";
				base_occu.value = "1";
			});
			util.add_grid_cell(
				grid,
				'<img src="assets/images/confirm.png"> Save/Update',
				() => {
					if(
						selected.original_string == null
						|| selected.original_string != base_ori.textContent
					)
					{
						for(let i = 0; i < this.project.config.ai_knowledge_base.length; ++i)
						{
							if(this.project.config.ai_knowledge_base[i].original == base_ori.textContent)
							{
								if(!window.confirm("Another entry exists for this original string, this will replace it.\nConfirm?"))
								{
									return;
								}
							}
						}
					}
					if(!/^[+-]?\d+$/.test(base_seen.value))
					{
						util.push_popup("\"Last seen\" isn't a valid integer");
						return;
					}
					if(!/^[+-]?\d+$/.test(base_occu.value))
					{
						util.push_popup("\"Occurences\" isn't a valid integer");
						return;
					}
					if(base_ori.textContent.trim() == "" || base_tl.textContent.trim() == "")
					{
						util.push_popup("The Original and Translations strings can't be empty");
						return;
					}
					this.post(
						"/api/update_knowledge",
						() => {
							this.loader.state = false;
							for(let i = selection.options.length - 1; i >= 1; i--)
							{
								selection.remove(i);
							}
							for(let i = 0; i < this.project.config.ai_knowledge_base.length; ++i)
							{
								let opt = util.add_to(
									selection,
									"option"
								);
								opt.value = i;
								opt.textContent = this.project.config.ai_knowledge_base[i].original + " / " + this.project.config.ai_knowledge_base[i].translation;
								if(this.project.config.ai_knowledge_base[i].original == base_ori.textContent)
									opt.selected = true;
							}
							selected.innerText = "Selected: " + base_ori.textContent + " / " + base_tl.textContent;
							selected.original_string = base_ori.textContent;
						},
						null,
						{
							name:this.project.name,
							entry:selected.original_string,
							original:base_ori.textContent,
							translation:base_tl.textContent,
							note:base_note.textContent,
							last_seen:base_seen.value,
							occurence:base_occu.value
						}
					);
				}
			);
			util.add_grid_cell(
				grid,
				'<img src="assets/images/trash.png"> Delete',
				() => {
					if(selected.original_string == null)
					{
						util.push_popup("No entry selected");
					}
					else
					{
						this.post(
							"/api/delete_knowledge",
							() => {
								this.loader.state = false;
								for(let i = selection.options.length - 1; i >= 1; i--)
								{
									selection.remove(i);
								}
								for(let i = 0; i < this.project.config.ai_knowledge_base.length; ++i)
								{
									let opt = util.add_to(
										selection,
										"option"
									);
									opt.value = i;
									opt.textContent = this.project.config.ai_knowledge_base[i].original + " / " + this.project.config.ai_knowledge_base[i].translation;
								}
								selection.options[0].selected = true;
								selected.innerText = "None selected";
								selected.original_string = null;
							},
							null,
							{
								name:this.project.name,
								entry:selected.original_string
							}
						);
					}
				}
			);
			selection.onchange = () => {
				const idx = selection.selectedIndex - 1;
				selected.innerText = "Selected: " + this.project.config.ai_knowledge_base[idx].original + " / " + this.project.config.ai_knowledge_base[idx].translation;
				selected.original_string = this.project.config.ai_knowledge_base[idx].original;
				base_ori.textContent = this.project.config.ai_knowledge_base[idx].original;
				base_tl.textContent = this.project.config.ai_knowledge_base[idx].translation;
				base_note.textContent = this.project.config.ai_knowledge_base[idx].note;
				base_seen.value = "" + this.project.config.ai_knowledge_base[idx].last_seen;
				base_occu.value = "" + this.project.config.ai_knowledge_base[idx].occurence;
			};
			this.update_main(fragment);
		}
		catch(err)
		{
			console.error("Exception thrown", err.stack);
			util.push_popup("An unexpected error occured.");
			this.routes.project(this.project.name);
		}
	}

	open_notes()
	{
		try
		{
			// top bar
			this.top_bar.update(
				"Notes",
				() => { // back callback
					this.routes.project(this.project.name);
				},
				"Take notes.",
				{
					home:1
				}
			);
			
			// main part
			let fragment = this.new_page();
			util.add_project_title(
				fragment,
				this.project.name
			);
			util.add_label(
				fragment,
				"Notepad"
			);
			const notepad = util.add_to(
				fragment,
				"div",
				{
					cls:["input", "noteinput"],
					navigable:true,
					br:true
				}
			);
			notepad.contentEditable = "plaintext-only";
			notepad.textContent = this.project.config.notes;
			util.add_interaction(fragment, '<img src="assets/images/confirm.png"> Save', () => {
				this.post(
					"/api/update_notes",
					null,
					null,
					{
						name:this.project.name,
						notes:notepad.textContent
					}
				);
			});
			this.update_main(fragment);
		}
		catch(err)
		{
			console.error("Exception thrown", err.stack);
			util.push_popup("An unexpected error occured.");
			this.routes.project(this.project.name);
		}
	}

	open_icon_set()
	{
		try
		{
			// top bar
			this.top_bar.update(
				"Set Project Icon",
				() => { // back callback
					this.routes.project(this.project.name);
				},
				"Set the project icon.",
				{
					home:1
				}
			);
			
			// main part
			let fragment = this.new_page();
			util.add_project_title(
				fragment,
				this.project.name
			);
			util.add_label(
				fragment,
				"Project Icon"
			);
			util.add_label(
				fragment,
				"Input the icon location",
				["left"]
			);
			const icon_path = util.add_to(
				fragment,
				"input",
				{
					cls:["input"],
					navigable:true
				}
			);
			icon_path.type = "text";
			icon_path.placeholder = "URL or Local Path or code";
			util.add_interaction(fragment, '<img src="assets/images/confirm.png"> Set', () => {
				this.post(
					"/api/update_icon",
					() => {
						this.routes.project(this.project.name);
					},
					null,
					{
						name:this.project.name,
						path:icon_path.value
					}
				);
			});
			util.add_to(
				fragment,
				"div",
				{
					cls:["label","left"],
					innerHTML:"Supports:<br>\
					• URL (Starting with http or https)<br>\
					• An absolute or relative local path (Example: C:\Users\...\icon.png or ../folder/icon.png)<br>\
					• A DLsite URL or RJ/RE/VJ codes (such as RJ000000 or RJ00000000)<br>\
					• A VNDB URL or code (such as v000)"
				}
			);
			this.update_main(fragment);
		}
		catch(err)
		{
			console.error("Exception thrown", err.stack);
			util.push_popup("An unexpected error occured.");
			this.routes.project(this.project.name);
		}
	}

	// translator pick menu /api/translator
	translator_menu(data)
	{
		try
		{
			const is_project = "config" in data;
			
			util.update_page_location("translator", (is_project ? this.project.name : null), null);
			
			// top bar
			this.top_bar.update(
				(is_project ? this.project.name + " Translators" : "Global Translators"),
				() => { // back callback
					if(is_project)
						this.routes.project(this.project.name);
					else
						this.routes.main();
				},
				"<ul>\
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
				</ul>",
				{
					home:is_project
				}
			);
			
			// main part
			let fragment = this.new_page();
			const list = data.list; // translator plugin list
			const possibles = ["current", "batch"];
			const possibles_text = ["Single Translation", "Batch Translation"];
			for(let t = 0; t < possibles.length; ++t)
			{
				if(list.length == 0)
				{
					util.add_label(
						fragment,
						"No Translator Plugin available",
						["left"]
					);
					break;
				}
				else
				{
					if(t == 0 && is_project) // add button to reset project setting (Only at the top)
					{
						util.add_project_title(
							fragment,
							this.project.name
						);
						util.add_interaction(
							fragment,
							'<img src="assets/images/trash.png"> Use RPGMTL Default',
							() => {
								this.post(
									"/api/update_translator",
									(result_data) => {
										util.push_popup("The Project Translators have been reset to the global settings.");
										this.routes.translator(this.project.name);
									},
									null,
									{
										name:this.project.name
									}
								);
							}
						);
					}
					// add text
					util.add_label(
						fragment,
						possibles_text[t],
						["left"]
					);
					// add select and option elements
					const sel = util.add_select(
						fragment,
						list,
						["smallinput"]
					);
					const tindex = t;
					// and confirmation button
					const elem = util.add_button(fragment, "Set", "assets/images/confirm.png", () => {
						let callback = (result_data) => {
							util.push_popup("The setting has been updated.");
							this.loader.state = false;
						};
						if(is_project)
						{
							this.post(
								"/api/update_translator",
								callback,
								null,
								{
									name:this.project.name,
									value:sel.value,
									index:tindex
								}
							);
						}
						else
						{
							this.post(
								"/api/update_translator",
								callback,
								null,
								{
									value:sel.value,
									index:tindex
								}
							);
						}
					});
					sel.value = data[possibles[t]];
				}
			}
			this.update_main(fragment);
		}
		catch(err)
		{
			console.error("Exception thrown", err.stack);
			util.push_popup("An unexpected error occured.");
			this.routes.main();
		}
	}

	// project creation /api/update_location
	project_creation(data)
	{
		// don't update page location here
		if(data.path == "" || data.path == null)
		{
			this.routes.main();
		}
		else
		{
			const path = data.path;
			// top bar
			this.top_bar.update(
				"Create a new Project",
				() => { // back callback
					this.routes.main();
				},
				"<ul>\
					<li>The Project Name has little importance, just make sure you know what it refers to.</li>\
					<li>If already taken, a number will be added after the name.</li>\
				</ul>\
				\
				The Icon supports:\
				<ul>\
					<li>URL (Starting with http or https).</li>\
					<li>An absolute or relative local path (Example: C:\Users\...\icon.png or ../folder/icon.png).</li>\
					<li>DLsite URL or RJ/RE/VJ codes (such as RJ000000 or RJ00000000).</li>\
					<li>A VNDB URL or code (such as v000).</li>\
				</ul>\
				\
				Keyboard shortcuts\
				<ul>\
					<li><b>F1</b> for the help.</li>\
					<li><b>Tab/Shit+Tab</b> and various <b>Arrow keys</b> to move around.</li>\
					<li><b>Enter</b> to interact.</li>\
					<li><b>Escape</b> to go back.</li>\
				</ul>"
			);
			
			// main part
			let fragment = this.new_page();
			util.add_label(
				fragment,
				"Folder & Project Name",
				["left"]
			);
			// project name input element
			const input = util.add_to(
				fragment,
				"input",
				{
					cls:["input"],
					navigable:true,
					br:true
				}
			);
			input.type = "text";
			// Icon
			util.add_label(
				fragment,
				"Icon path or URL",
				["left"]
			);
			const icon = util.add_to(
				fragment,
				"input",
				{
					cls:["input"],
					navigable:true,
					br:true
				}
			);
			icon.type = "text";
			icon.placeholder = "Optional";
			
			let tmp = path.split("/"); // set input default value
			if(tmp.length >= 1)
			{
				input.value = tmp[tmp.length-1];
			}
			else
			{
				input.value = "Project";
			}
			
			// confirm button
			util.add_interaction(
				fragment,
				'<img src="assets/images/confirm.png"> Create',
				() => {
					this.loader.text = "Creating the project...";
					if(input.value.trim() != "")
					{
						this.routes.new_project(path, input.value, icon.value);
					}
				}
			);
			
			// explanation
			util.add_label(
				fragment,
				"After confirming, a backup of the game files will be made in this project folder.\nYou'll then have to set your Project Settings and Extract the strings.",
				["left"]
			);
			this.update_main(fragment);
		}
	}

	// display project options (called by many API and more, data is optional and unused)
	project_menu(data = null)
	{
		try
		{
			util.update_page_location("menu", this.project.name, null);
			
			// top bar
			this.top_bar.update(
				this.project.name,
				() => { // back callback
					this.routes.main();
				},
				"<ul>\
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
					<li><b>Save and close</b> if you must do modifications on the local files, using external scripts or whatever.</li>\
				</ul>\
				<ul>\
					<li><b>Replace Strings in batch</b> allows you to do batch replacement of case-sensitive strings.</li>\
					<li><b>Backup Control</b> to open the list of backups if you need to revert the project strings data to an earlier state.</li>\
					<li><b>Knowledge Base</b> to open the list of knowledge entries for AI translations.</li>\
					<li><b>Notepad</b> is used to note things.</li>\
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
				</ul>",
				{
					home:1
				}
			);
			
			// main part
			// here we add various buttons
			// some only appear if files have been parsed
			let fragment = this.new_page();
			util.add_project_title(
				fragment,
				this.project.name
			);
			util.add_label(
				fragment,
				"Imported from: " + this.project.config.path,
				["left", "smalltext"]
			);
			let grid = null;
			// translate options
			if(this.project.config.version)
			{
				util.add_label(
					fragment,
					"Translate",
					["left"]
				);
				grid = util.add_to(
					fragment,
					"div",
					{
						cls:["grid"],
						br:true
					}
				);
				util.add_grid_cell(grid, '<img src="assets/images/folder.png"> Browse Files', () => {
					this.routes.browse(this.project.name, "");
				});
				util.add_grid_cell(grid, '<img src="assets/images/bandaid.png"> Add a Fix', () => {
					this.routes.patches(this.project.name);
				});
				util.add_grid_cell(
					grid,
					'<img src="assets/images/translate.png"> Batch Translate',
					(e) => {
						if(
							e.ctrlKey
							|| window.confirm("Are you sure you wish to translate the whole game?\nIt will be time consuming.\nMake sure your settings are set properly.")
						) // confirmation / shortcut to insta confirm
						{
							this.loader.text = "Translating the whole game, go do something else...";
							this.post(
								"/api/translate_project",
								() => this.routes.redirect_to_project(),
								() => this.routes.redirect_to_project(),
								{
									name:this.project.name
								}
							);
						}
					}
				);
			}
			// settings options
			util.add_label(
				fragment,
				"Settings",
				["left"]
			);
			grid = util.add_to(
				fragment,
				"div",
				{
					cls:["grid"],
					br:true
				}
			);
			util.add_grid_cell(
				grid,
				'<img src="assets/images/setting.png"> Project Settings',
				() => {
					this.routes.settings(this.project.name);
				}
			);
			util.add_grid_cell(
				grid,
				'<img src="assets/images/translate.png"> Project Translators',
				() => {
					this.routes.translator(this.project.name);
				}
			);
			// main actions
			util.add_label(
				fragment,
				"Actions",
				["left"]
			);
			grid = util.add_to(
				fragment,
				"div",
				{
					cls:["grid"],
					br:true
				}
			);
			util.add_grid_cell(
			grid,
				'<img src="assets/images/update.png"> Update the Game Files',
				() => {
					this.local_browse("Update project files", "Select the Game executable.", 1);
				}
			);
			util.add_grid_cell(
				grid,
				'<img src="assets/images/export.png"> Extract the Strings',
				(e) => {
					if(
						e.ctrlKey
						|| window.confirm("Extract the strings?")
					) // confirmation / shortcut to insta confirm
					{
						this.loader.text = "Extracting, be patient...";
						this.post(
							"/api/extract",
							() => this.routes.redirect_to_project(),
							() => this.routes.main(),
							{
								name:this.project.name
							}
						);
					}
				}
			);
			if(this.project.config.version)
			{
				util.add_grid_cell(
					grid,
					'<img src="assets/images/release.png"> Release a Patch',
					() => {
						this.loader.text = "The patch is being generated in the release folder...";
						this.post(
							"/api/release",
							() => this.routes.redirect_to_project(),
							null,
							{
								name:this.project.name
							}
						);
					}
				);
			}
			util.add_grid_cell(grid, '<img src="assets/images/cancel.png"> Save and close', () => {
				this.post(
					"/api/unload",
					() => this.routes.main(),
					null,
					{
						name:this.project.name
					}
				);
			});
			if(this.project.config.version)
			{
				util.add_grid_cell(
					grid,
					'<img src="assets/images/copy.png"> Replace Strings in batch',
					() => {
						this.replace_page();
					}
				);
				util.add_grid_cell(
					grid,
					'<img src="assets/images/copy.png"> Backup Control',
					() => {
						this.routes.backups(this.project.name);
					}
				);
			}
			util.add_grid_cell(
				grid,
				'<img src="assets/images/ai.png"> Knowledge Base',
				() => {
					this.open_knowledge();
				}
			);
			util.add_grid_cell(
				grid,
				'<img src="assets/images/note.png"> Notepad',
				() => {
					this.open_notes();
				}
			);
			util.add_grid_cell(
				grid,
				'<img src="assets/images/icon_set.png"> Set Project Icon',
				() => {
					this.open_icon_set();
				}
			);
			if(this.project.config.version)
			{
				util.add_grid_cell(
					grid,
					'<img src="assets/images/import.png"> Import RPGMTL Strings',
					() => {
						this.local_browse(
							"Import RPGMTL",
							"Select an old RPGMTL strings file.",
							2
						);
					}
				);
				util.add_grid_cell(
					grid,
					'<img src="assets/images/import.png"> Import RPGMakerTrans v3 Strings',
					() => {
						this.local_browse(
							"Import RPGMAKERTRANSPATCH",
							"Select a RPGMAKERTRANSPATCH file.",
							3
						);
					}
				);
				if(this.tools.list.length > 0)
				{
					util.add_label(
						fragment,
						"Tools",
						["left"]
					);
					grid = util.add_to(
						fragment,
						"div",
						{
							cls:["grid"],
							br:true
						}
					);
					this.add_tools(
						grid,
						util.add_grid_cell,
						(this.project.config.bookmarked_tools ?? []),
						false
					);
					util.add_grid_cell(
						grid,
						'<img src="assets/images/star.png"> All Tools',
						() => {
							this.open_tool_list();
						}
					);
				}
			}
			this.update_main(fragment);
		}
		catch(err)
		{
			console.error("Exception thrown", err.stack);
			util.push_popup("An unexpected error occured.");
			this.routes.main();
		}
	}

	// generic function to add a search bar on top of the browse file page
	addSearchBar(node, bp, defaultVal = null)
	{
		// input element
		util.add_label(
			node,
			"Search",
			["left", "smalltext", "inline"]
		);
		const input = util.add_to(
			node,
			"textarea",
			{
				cls:["input", "searchinput", "inline", "customarea"],
				navigable:true
			}
		);
		if(defaultVal != null)
		{
			input.value = defaultVal;
		}
		else if(this.search.string != null) // set last string searched if not null
		{
			input.value = this.search.string;
		}
		else
		{
			input.value = "";
		}
		input.rows = "" + input.value.split("\n").length;
		input.addEventListener('input', () => { // auto update rows on input
			input.rows = "" + input.value.split("\n").length;
		});
		
		// add confirm button
		const button = util.add_button(
			node,
			"Search",
			"assets/images/search.png",
			() => {
				if(input.value != "")
				{
					this.routes.search(
						this.project.name, bp,
						input.value,
						useorigin.classList.contains("green"),
						casesensi.classList.contains("green"),
						!contains.classList.contains("green")
					);
				}
			}, 
			true
		);
		input.addEventListener('keypress', (event) => {
			if(event.key === 'Enter' && event.shiftKey)
			{
				event.preventDefault();
				button.click();
			}
		});
		util.add_to(node, "br");
		// setting buttons
		util.add_label(
			node,
			"Search settings",
			["left", "smalltext", "inline"]
		);
		const useorigin = util.add_button(
			node,
			"Search Original Strings", "assets/images/original_string.png",
			() => {
				useorigin.classList.toggle("green");
			},
			true
		);
		if(this.search.useorigin)
		{
			useorigin.classList.toggle("green", true);
		}
		const casesensi = util.add_button(
			node,
			"Case Sensitive", "assets/images/search_case.png",
			() => {
				casesensi.classList.toggle("green");
			},
			true
		);
		if(this.search.casesensitive)
		{
			casesensi.classList.toggle("green", true);
		}
		const contains = util.add_button(
			node,
			"Exact Match",
			"assets/images/search_exact.png",
			() => {
				contains.classList.toggle("green");
			},
			true
		);
		if(!this.search.contains)
		{
			contains.classList.toggle("green", true);
		}
	}

	// search original button, used in index.html
	search_this()
	{
		let urlparams = new URLSearchParams("");
		urlparams.set("page", "search_string");
		urlparams.set("name", this.project.name);
		urlparams.set("params", util.stob64(JSON.stringify({
			name:this.project.name,
			path:this.project.last_data.path,
			search:document.getElementById('edit-ori').textContent,
			useorigin:true,
			casesensitive:true,
			contains:false
		})));
		window.open(window.location.pathname + '?' + urlparams.toString(), '_blank').focus(); // open in another tab
	}

	// open folder /api/browse
	browse_files(data)
	{
		try
		{
			this.search.string = null;
			const bp = data.path;
			util.update_page_location("browse", this.project.name, bp);
			// top bar
			this.top_bar.update(
				"Path: " + bp,
				() => { // back callback
					let returnpath = bp.includes('/') ? bp.split('/').slice(0, bp.split('/').length-2).join('/')+'/' : "";
					// returnpath is the path of the parent folder
					if(bp == "") // current folder is the root, so back to menu
					{
						this.routes.project(this.project.name);
					}
					else
					{
						if(returnpath == '/') returnpath = ''; // if return path is a single slash, set to empty first
						this.routes.browse(this.project.name, returnpath);
					}
				},
				"<ul>\
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
				</ul>",
				{
					home:1,
					project:1,
					refresh:1,
					refresh_callback:() => {
						this.routes.browse(this.project.name, bp);
					}
				}
			);
			
			// main part
			let fragment = this.new_page();
			util.add_project_title(
				fragment,
				this.project.name
			);
			// add the string search
			this.addSearchBar(fragment, bp);
			
			// add completion indicator
			this.progress.add_tracker(fragment);
			
			let first_element = null;
			util.add_stylized_path(
				this,
				fragment,
				bp
			);
			// go over folders
			for(let i = 0; i < data.folders.length; ++i)
			{
				const t = data.folders[i];
				let div = util.add_to(
					fragment,
					"div",
					{
						cls:["interact"],
						navigable:true
					}
				);
				if(first_element == null)
				{
					first_element = div;
				}
				if(t == "..") // special one indicating we aren't on the root level
				{
					div.innerHTML = '<img src="assets/images/back.png"> ..';
				}
				else if(this.project.config.files[t.slice(0, -1)] != undefined) // for archive type files
				{
					div.innerHTML = '<img src="assets/images/archive.png"> ' + t;
					div.classList.add("archive");
				}
				else
				{
					div.innerHTML = '<img src="assets/images/folder.png"> ' + t;
				}
				div.onclick = () => {
					if(t == "..") // used for the "parent folder" button
					{
						let s = bp.split("/"); // at least 2 elements in s means there is one slash in the path, i.e. we aren't in the root level
						if(s.length == 2)
						{
							this.routes.browse(
								this.project.name,
								""
							);
						}
						else
						{
							this.routes.browse(
								this.project.name,
								s.slice(0, s.length-2).join("/") + "/"
							);
						}
					}
					else // open whatever folder it is
					{
						this.routes.browse(
							this.project.name,
							t
						);
					}
				};
			}
			util.add_label(
				fragment,
				"List of Files",
				["left"]
			);
			// possible class sets
			let cls = [
				["interact", "file-path-container"],
				["interact", "file-path-container", "disabled"]
			];
			let scrollTo = null; // contains element to scroll to
			for(const [key, value] of Object.entries(data.files))
			{
				// add button
				const button = util.add_to(
					fragment,
					"div",
					{
						cls:cls[+value],
						id:"text:"+key,
						navigable:true,
						onclick:(e) => {
							if(e.ctrlKey) // ignore shortcut
							{
								this.post(
									"/api/ignore_file",
									(result_data) => {
										this.update_file_list(result_data);
										// update completion
										this.progress.compute_browse_view(this.project, bp);
									},
									null,
									{
										name:this.project.name,
										path:key,
										state:+!button.classList.contains("disabled")
									}
								);
							}
							else
							{
								this.loader.text = "Opening " + key + "...";
								this.routes.file(this.project.name, key);
							}
						}
					}
				);
				if(first_element == null)
				{
					first_element = button;
				}
				this.progress.add_path_info(
					button,
					key,
					this.project.config.files[key]
				);
				if(key == this.lastfileopened) // if this is the last opened file
				{
					scrollTo = button; // store it
				}
			}
			// add space at the bottom
			util.add_spacer(fragment);
			// set completion tracker
			this.progress.compute_browse_view(this.project, bp);
			this.update_main(fragment).then(() => {
				if(scrollTo != null) // scroll to last opened file
				{
					scrollTo.scrollIntoView();
					scrollTo.focus({preventScroll: true});
					this.nav.update_focus(scrollTo);
				}
				else if(first_element)
				{
					first_element.focus({preventScroll: true});
					this.nav.index = 1;
				}
			});
			this.lastfileopened = null; // and clear it
		}
		catch(err)
		{
			this.lastfileopened = null;
			console.error("Exception thrown", err.stack);
			util.push_popup("An unexpected error occured.");
			this.routes.project(this.project.name);
		}
	}

	// search a string /api/search_string
	// it copy/paste stuff from the browse function
	string_search(data)
	{
		try
		{
			const bp = data.path;
			this.search.string = data.search;
			this.search.useorigin = data.useorigin;
			this.search.casesensitive = data["case"];
			this.search.contains = data.contains;
			util.update_page_location(
				"search_string",
				this.project.name,
				{
					path:bp,
					search:this.search.string,
					useorigin:this.search.useorigin,
					casesensitive:this.search.casesensitive,
					contains:this.search.contains
				}
			);
			// top bar
			this.top_bar.update(
				"Search Results",
				() => { // back callback
					if(bp in data.files)
					{
						this.routes.file(this.project.name, data.path);
					}
					else
					{
						this.routes.browse(this.project.name, data.path);
					}
				},
				"<ul>\
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
					<li><b>Ctrl+P</b> to go to the this.project page.</li>\
					<li><b>Ctrl+R</b> to reload.</li>\
				</ul>",
				{
					home:1,
					project:1
				}
			);
			
			// main part
			let fragment = this.new_page();
			util.add_project_title(
				fragment,
				this.project.name
			);
			this.addSearchBar(fragment, bp, data.search);
			
			util.add_label(
				fragment,
				"Results",
				["left"]
			);
			let cls = [
				["interact", "file-path-container"],
				["interact", "file-path-container", "disabled"]
			];
			// list files
			let first_element = null;
			for(const [key, value] of Object.entries(data.files))
			{
				const button = util.add_to(
					fragment,
					"div",
					{
						cls:cls[+value],
						id:"text:"+key,
						navigable:true,
						onclick:(e) => {
							if(e.ctrlKey) // disable shortcut
							{
								this.post(
									"/api/ignore_file",
									(result_data) => this.update_file_list(result_data),
									null,
									{
										name:this.project.name,
										path:key,
										state:+!button.classList.contains("disabled")
									}
								);
							}
							else
							{
								this.loader.text = "Opening " + key + "...";
								this.routes.file(this.project.name, key);
							}
						}
					}
				);
				this.progress.add_path_info(
					button,
					key,
					this.project.config.files[key]
				);
				if(first_element == null)
				{
					first_element = button;
				}
			}
			this.update_main(fragment, first_element);
		}
		catch(err)
		{
			console.error("Exception thrown", err.stack);
			util.push_popup("An unexpected error occured.");
			this.routes.project(this.project.name);
		}
	}

	// open fix list /api/patches
	browse_patches(data)
	{
		try
		{
			util.update_page_location("patches", this.project.name, null);
			// top part
			this.top_bar.update(
				this.project.name,
				() => { // back callback
					this.routes.project(this.project.name);
				},
				"<ul>\
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
				</ul>",
				{
					home:1,
					project:1
				}
			);
			
			// main part
			let fragment = this.new_page();
			util.add_project_title(
				fragment,
				this.project.name
			);
			util.add_label(
				fragment,
				"Fix List",
				["left"]
			);
			// list patches
			for(const [key, value] of Object.entries(this.project.config.patches))
			{
				// add button to open
				util.add_interaction(fragment, '<img src="assets/images/bandaid.png"> ' + key, () => {
					this.routes.open_patch(this.project.name, key);
				});
			}
			util.add_spacer(fragment);
			// add create button
			util.add_interaction(fragment, '<img src="assets/images/new.png"> Create', () => {
				this.edit_patch({});
			});
			// add patch.py buttons
			let grid = util.add_to(
				fragment,
				"div",
				{
					cls:["grid"],
					br:true
				}
			);
			util.add_grid_cell(grid, '<img src="assets/images/export.png"> Export', (e) => {
				if(
					e.ctrlKey
					|| window.confirm("It will overwrite projects/" + this.project.name + "/patch.py\nContinue?")
				) // confirmation / shortcut to insta confirm
				{
					this.post(
						"/api/export_patch",
						(result_data) => this.browse_patches(result_data),
						(result_data) => this.browse_patches(result_data),
						{
							name:this.project.name
						}
					);
				}
			});
			util.add_grid_cell(grid, '<img src="assets/images/import.png"> Import', (e) => {
				if(
					e.ctrlKey
					|| window.confirm("The patches will be overwritten by the content of projects/" + this.project.name + "/patch.py\nContinue?")
				) // confirmation / shortcut to insta confirm
				{
					this.post(
						"/api/import_patch",
						(result_data) => this.browse_patches(result_data),
						(result_data) => this.browse_patches(result_data),
						{
							name:this.project.name
						}
					);
				}
			});
			this.update_main(fragment);
		}
		catch(err)
		{
			console.error("Exception thrown", err.stack);
			util.push_popup("An unexpected error occured.");
			this.routes.project(this.project.name);
		}
	}

	// edit a fix /api/open_patch
	edit_patch(data)
	{
		try
		{
			const key = data.key; // patch key. Note: CAN be null
			if(key != null)
				util.update_page_location("open_patch", this.project.name, key);
			// top bar
			this.top_bar.update(
				"Create a Fix",
				() => { // back callback
					this.routes.patches(this.project.name);
				},
				"<ul>\
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
				</ul>",
				{
					home:1,
					project:1
				}
			);
			
			// main part
			let fragment = this.new_page();
			// add various input and text elements
			util.add_project_title(
				fragment,
				this.project.name
			);
			util.add_label(
				fragment,
				"Filename match",
				["left"]
			);
			util.add_to(
				fragment,
				"input",
				{
					cls:["input"],
					id:"filter",
					navigable:true,
					br:true
				}
			).type = "text";
			util.add_label(
				fragment,
				"Python Code",
				["left"]
			);
			util.add_to(
				fragment,
				"div",
				{
					cls:["input"],
					id:"fix",
					navigable:true,
					br:true
				}
			).contentEditable = "plaintext-only";
			// add confirm button
			util.add_interaction(
				fragment,
				'<img src="assets/images/confirm.png"> Confirm',
				() => {
					let newkey = document.getElementById("filter").value;
					let code = document.getElementById("fix").textContent;
					if(newkey.trim() != "" && code.trim() != "")
					{
						this.post(
							"/api/update_patch",
							(result_data) => this.browse_patches(result_data),
							null,
							{
								name:this.project.name,
								key:key,
								newkey:newkey,
								code:code
							}
						);
					}
					else
					{
						util.push_popup("At least one field is empty");
					}
				}
			);
			util.add_interaction(
				fragment,
				'<img src="assets/images/trash.png"> Delete',
				() => {
					this.post(
						"/api/update_patch",
						(result_data) => this.browse_patches(result_data),
						null,
						{
							name:this.project.name,
							key:key
						}
					);
				}
			);
			util.add_to(
				fragment,
				"div",
				{
					cls:["label", "left"],
					innerText:"Helper references"
				}
			)
			util.add_to(
				fragment,
				"pre",
				{
					cls:["documentation"],
					innerText:"Byte Access:\n• helper.content -> str\n• helper.content = modified_bytes\n\n• helper.to_str(encoding='utf-8') -> str\n• helper.from_str(modified_string, encoding='utf-8')\n\nJSON Access:\n• helper.to_json(encoding='utf-8') -> Any\n• helper.from_json(modified_data, encoding='utf-8', ensure_ascii=False, indent=None, separators=None)\n\nConfirm modifications:\n• helper.modified = True"
				}
			);
			
			if(key != null)
			{
				fragment.getElementById("filter").value = key;
				fragment.getElementById("fix").textContent = this.project.config.patches[key];
			}
			this.update_main(fragment);
		}
		catch(err)
		{
			console.error("Exception thrown", err.stack);
			util.push_popup("An unexpected error occured.");
			this.routes.project(this.project.name);
		}
	}

	// open backup list /api/backups
	backup_list(data)
	{
		try
		{
			util.update_page_location("backups", this.project.name, null);
			// top part
			this.top_bar.update(
				this.project.name,
				() => { // back callback
					this.routes.project(this.project.name);
				},
				"<ul>\
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
				</ul>",
				{
					home:1,
					project:1
				}
			);
			
			// main part
			let fragment = this.new_page();
			util.add_project_title(
				fragment,
				this.project.name
			);
			util.add_label(
				fragment,
				"Backup List",
				["left"]
			);
			if(data.list.length == 0)
			{
				util.add_label(
					fragment,
					"No backup available",
					["left", "block", "inline"]
				);
			}
			// list project backups
			for(const elem of data.list)
			{
				// add button to load it
				util.add_to(
					fragment,
					"div",
					{
						cls:["interact", "text-button", "inline"],
						innerHTML:'<img src="assets/images/copy.png"> Use',
						onclick:(e) => {
							if(
								e.ctrlKey
								|| window.confirm("Load this backup?")
							) // confirmation / shortcut to insta confirm
							{
								this.post(
									"/api/load_backup",
									() => this.routes.redirect_to_project(),
									null,
									{
										name:this.project.name,
										file:elem[0]
									}
								);
							}
						}
					}
				);
				util.add_label(
					fragment,
					elem[0],
					["left", "block", "inline"]
				);
				// add backup infos
				let size = util.filesizeToStr(elem[1]);
				util.add_label(
					fragment,
					size,
					["left", "block", "inline", "smalltext"]
				);
				util.add_label(
					fragment,
					new Date(elem[2]*1000).toISOString().split('.')[0].replace('T', ' '),
					["left", "block", "inline", "smalltext"]
				);
				util.add_to(fragment, "br");
			}
			this.update_main(fragment);
		}
		catch(err)
		{
			console.error("Exception thrown", err.stack);
			util.push_popup("An unexpected error occured.");
			this.routes.project(this.project.name);
		}
	}

	// update file elements /api/ignore_file
	update_file_list(data)
	{
		try
		{
			this.loader.state = false;
			for(const [key, value] of Object.entries(data.files)) // simply update disabled class
			{
				let file = document.getElementById("text:"+key);
				if(file)
				{
					file.classList.toggle("disabled", value);
				}
			}
		}
		catch(err)
		{
			console.error("Exception thrown", err.stack);
			util.push_popup("An unexpected error occured.");
			this.routes.project(this.project.name);
		}
	}

	// Prepare string space for string list
	prepareGroupOn(node, i)
	{
		let base = util.add_to(
			node,
			"div",
			{
				cls:["interact-group"],
				br:true
			}
		); // base container
		let group = util.add_to(
			base,
			"span",
			{
				cls:["smalltext"],
				id:i,
				br:true
			}
		); // group container
		// add group name OR index
		if(this.project.string_groups[i][0] != "")
		{
			group.textContent = this.project.string_groups[i][0];
		}
		else
		{
			group.textContent = "#"+(i+1);
		}
		// iterate over strings of this group
		for(let j = 1; j < this.project.string_groups[i].length; ++j)
		{
			const span = util.add_to(
				base,
				"span",
				{
					cls:["interact", "string-group"],
					navigable:true,
					br:true
				}
			); // add container
			span.group = i;
			span.string = j;
			
			let marker = util.add_to(
				span,
				"div",
				{
					cls:["marker", "inline", "marker-pad-left"]
				}
			); // left marker (modified, plugins...)
			let user_marker = util.add_to(
				span,
				"div",
				{
					cls:["marker", "inline", "marker-pad-right"]
				}
			); // second marker (user color marker)
			user_marker.state = 0;
			
			let original = util.add_to(
				span,
				"pre",
				{
					cls:["label", "inline", "smalltext", "string-area", "original"]
				}
			); // original string
			original.group = i;
			original.string = j;
			original.raw_string = this.project.strings[this.project.string_groups[i][j][0]][0];
			original.textContent = original.raw_string;
			
			let translation = util.add_to(
				span,
				"pre",
				{
					cls:["label", "inline", "smalltext", "string-area", "translation"]
				}
			); // translated string
			translation.group = i;
			translation.string = j;
			translation.raw_string = "";
			
			this.strtablecache.push([span, marker, translation, original, user_marker]); // add to strtablecache
			// add string interactions
			span.onclick = (e) => {
				if(e.ctrlKey && !e.shiftKey && !e.altKey) // single disable
				{
					this.disable_string(span);
					util.stop_event(e);
				}
				else if(e.ctrlKey && !e.shiftKey && e.altKey) // multi disable
				{
					this.multi_disable_string(span);
					util.stop_event(e);
				}
				else if(!e.ctrlKey && e.shiftKey && !e.altKey) // unlink
				{
					if(!this.edit.is_open())
					{
						this.unlink_string(span);
						util.stop_event(e);
					}
				}
			};
			// right click interaction
			span.oncontextmenu = (e) => {
				if(util.check_sp_key(e, 0, 0, 1)) // single disable
				{
					this.all_disable_string(span);
					util.stop_event(e);
				}
				else if(util.check_sp_key(e, 0, 0, 0)) // marker toggle (+1)
				{
					this.cycle_marker(span, 1);
					util.stop_event(e);
				}
				else if(util.check_sp_key(e, 1, 0, 0)) // marker toggle (-1)
				{
					this.cycle_marker(span, -1);
					util.stop_event(e);
				}
			}
			// add original string copy
			original.onclick = (e) => {
				if(util.check_sp_key(e, 0, 1, 0))
				{
					this.copy_original(original);
					this.nav.update_focus(span);
					util.stop_event(e);
				}
			};
			// add translated string copy AND open
			translation.onclick = (e) => {
				if(!e.ctrlKey && !e.shiftKey)
				{
					if(e.altKey)
					{
						this.copy_translated(translation);
					}
					else
					{
						this.open_string(span);
					}
					this.nav.update_focus(span);
					util.stop_event(e);
				}
			};
		}
	}

	// string clicks:
	disable_string(elem)
	{
		this.loader.text = "Updating...";
		this.post(
			"/api/update_string",
			(result_data) => this.update_string_list(result_data),
			null,
			{
				setting:1,
				version:this.project.version,
				name:this.project.name,
				path:this.project.last_data.path,
				group:elem.group,
				index:elem.string
			}
		);
		this.nav.update_focus(elem);
	}

	multi_disable_string(elem)
	{
		this.loader.text = "Updating...";
		this.post(
			"/api/update_string",
			(result_data) => this.update_string_list(result_data),
			null,
			{
				setting:2,
				version:this.project.version,
				name:this.project.name,
				path:this.project.last_data.path,
				group:elem.group,
				index:elem.string
			}
		);
		this.nav.update_focus(elem);
	}

	all_disable_string(elem)
	{
		this.loader.text = "Updating...";
		this.post(
			"/api/update_string",
			(result_data) => this.update_string_list(result_data),
			null,
			{
				setting:3,
				version:this.project.version,
				name:this.project.name,
				path:this.project.last_data.path,
				group:elem.group,
				index:elem.string
			}
		);
		this.nav.update_focus(elem);
	}

	unlink_string(elem)
	{
		this.loader.text = "Updating...";
		this.post(
			"/api/update_string",
			(result_data) => this.update_string_list(result_data),
			null,
			{
				setting:0,
				version:this.project.version,
				name:this.project.name,
				path:this.project.last_data.path,
				group:elem.group,
				index:elem.string
			}
		);
		this.nav.update_focus(elem);
	}

	cycle_marker(elem, shift)
	{
		this.post(
			"/api/update_marker",
			(result_data) => this.update_string_list(result_data),
			null,
			{
				name:this.project.name,
				path:this.project.last_data.path,
				id:this.project.string_groups[elem.group][elem.string][0],
				value:(
					(
						this.project.strings[this.project.string_groups[elem.group][elem.string][0]][3]
						+ shift
						+ this.constant.marker_classes.length
					) % this.constant.marker_classes.length
				)
			}
		);
	}

	copy_original(elem)
	{
		if(navigator.clipboard != undefined)
		{
			navigator.clipboard.writeText(elem.textContent);
			util.push_popup('The Original has been copied');
		}
		else
		{
			util.push_popup('You need to be on a secure origin to copy');
		}
	}

	copy_translated(elem)
	{
		if(navigator.clipboard != undefined)
		{
			navigator.clipboard.writeText(elem.textContent);
			util.push_popup('The Translation has been copied');
		}
		else
		{
			util.push_popup('You need to be on a secure origin to copy');
		}
	}

	open_string(elem)
	{
		// string from project data
		let ss = this.project.string_groups[elem.group][elem.string];
		// update bottom part
		// set occurence count
		const occurence = this.project.strings[this.project.string_groups[elem.group][elem.string][0]][2];
		// set original string text
		const original = this.project.strings[ss[0]][0];
		let translation = original;
		// set textarea with current translation
		if(ss[2]) // local/unlinked
		{
			if(ss[1] != null)
			{
				translation = ss[1];
			}
		}
		else if(this.project.strings[ss[0]][1] != null) // global
		{
			translation = this.project.strings[ss[0]][1];
		}
		// make element visible
		this.edit.open(occurence, original, translation);
		// set this span element as the current string being edited
		if(this.currentstr != null)
		{
			this.currentstr.classList.toggle("selected-line", false);
		}
		this.currentstr = elem;
		this.currentstr.classList.toggle("selected-line", true);
	}

	// open a file content /api/file
	open_file(data)
	{
		try
		{
			// init stuff
			this.project.strings = data.strings;
			this.project.string_groups = data.list;
			this.project.last_data = data;
			this.lastfileopened = data.path;
			
			util.update_page_location("file", this.project.name, this.lastfileopened);
			
			// folder path
			const returnpath = this.lastfileopened.includes('/') ? this.lastfileopened.split('/').slice(0, this.lastfileopened.split('/').length-1).join('/')+'/' : "";
			
			// determinate the previous and next file in the same folder
			let prev_file = null;
			let next_file = null;
			let file_same_folder = [];
			for(let f in this.project.config.files)
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
				let f_index = file_same_folder.indexOf(this.lastfileopened);
				prev_file = file_same_folder[(f_index - 1 + file_same_folder.length) % file_same_folder.length];
				next_file = file_same_folder[(f_index + 1) % file_same_folder.length];
			}
			
			// top bar
			this.top_bar.update(
				"File: " + this.lastfileopened,
				() => { // back callback
					this.edit.close();
					if(this.search.string != null) // return to search result if we came from here
					{
						this.routes.search(
							this.project.name,
							returnpath,
							this.search.string,
							this.search.useorigin,
							this.search.casesensitive,
							this.search.contains
						);
					}
					else
					{
						this.routes.browse(
							this.project.name,
							returnpath
						);
					}
				},
				"<ul>\
					<li><b>Right Click</b> or <b>Ctrl+B</b> on a line to cycle the global marker. <b>Shift</b> to cycle in reverse.</li>\
					<li><b>Ctrl+Click</b> or <b>Ctrl+Y</b> on a line to make it be <b>ignored</b> during the release process.</li>\
					<li><b>Alt+Ctrl+Click</b> or <b>Ctrl+Shift+Y</b> on a line to <b>ignore ALL</b> occurences of this string in this file.</li>\
					<li><b>Ctrl+Right Click</b> or <b>Ctrl+Alt+Y</b> on a line to <b>ignore ALL</b> occurences of this string in this this.project.</li>\
					<li><b>Shift+Click</b> or <b>Ctrl+U</b> on a line to <b>unlink</b> it, if you need to set it to a translation specific to this part of the file.</li>\
					<li><b>Alt+Click</b> or <b>Ctrl+O</b> on the original string (on the left) to copy it.</li>\
					<li><b>Alt+Click</b> or <b>Ctrl+I</b> on the translated string (on the right) to copy it.</li>\
					<li><b>Click</b> or press <b>Enter</b> on the translated string (on the right) to edit it.</li>\
					<li><b>Ctrl+Space</b> to scroll to the next untranslated <b>enabled</b> string.</li>\
					<li><b>Shift+Ctrl+Space</b> to scroll to the next untranslated string.</li>\
					<li><b>Alt+Ctrl+Space</b> to scroll to the next unlinked string.</li>\
					<li>On top, if available, you'll find <b>Plugin Actions</b> for this file.</li>\
					<li>You'll also find the <b>Translate the File</b> button.</li>\
				</ul>\
				\
				Other shortcuts\
				<ul>\
					<li><b>F1</b> for the help.</li>\
					<li><b>Tab/Shit+Tab</b> and various <b>Arrow keys</b> to move around.</li>\
					<li><b>Enter</b> to interact.</li>\
					<li><b>Escape</b> to go back if the edit window is closed.</li>\
					<li><b>Ctrl+H</b> to go to the home page.</li>\
					<li><b>Ctrl+P</b> to go to the this.project page.</li>\
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
				</ul>",
				{
					home:1,
					project:1,
					refresh:1,
					refresh_callback:() => {
						this.edit.close();
						this.routes.file(this.project.name, this.lastfileopened);
					},
					slider:1,
					file_nav:+(prev_file != null),
					file_nav_previous_callback:() => {
						this.edit.close();
						this.routes.file(this.project.name, prev_file);
					},
					file_nav_next_callback:() => {
						this.edit.close();
						this.routes.file(this.project.name, next_file);
					}
				}
			);
			
			// main part
			let fragment = this.new_page();
			
			const topsection = util.add_project_title(
				fragment,
				this.project.name
			);
			this.progress.add_tracker(fragment);
			util.add_stylized_path(
				this,
				fragment,
				this.lastfileopened
			);
			let previous_plugin = null;
			// list file actions
			for(const [key, [plugin_name, icon, value]] of Object.entries(data.actions))
			{
				if(previous_plugin != plugin_name)
				{
					util.add_label(
						fragment,
						plugin_name + " Plugin",
						["left", "interact-group", "smalltext"]
					);
					previous_plugin = plugin_name;
				}
				util.add_interaction(
					fragment,
					(
						'<img src="'
						+ (
							icon == null
							? "assets/images/setting.png"
							: icon
						)
						+ '"> '
						+ value
					),
					(e) => {
						if(
							e.ctrlKey
							|| window.confirm("Use " + value + "?")
						) // confirmation / shortcut to insta confirm
						{
							this.post("/api/file_action",
								() => {
									this.routes.file(this.project.name, this.lastfileopened);
								},
								() => { // reload the file
									this.routes.browse(this.project.name, returnpath);
								},
								{
									name:this.project.name,
									path:this.lastfileopened,
									version:this.project.version,
									key:key
								}
							);
						}
					}
				);
			}
			util.add_label(
				fragment,
				"Other Actions",
				["left", "interact-group", "smalltext"]
			);
			// add translate this file button
			util.add_interaction(
				fragment,
				'<img src="assets/images/translate.png"> Translate the File',
				(e) => {
					if(
						e.ctrlKey
						|| window.confirm("Translate this file?\nIt can take time.")
					) // confirmation / shortcut to insta confirm
					{
						this.loader.text = "Translating this file, be patient...";
						this.post(
							"/api/translate_file",
							(result_data) => this.update_string_list(result_data),
							() => {
								this.edit.close();
								this.routes.browse(this.project.name, returnpath);
							},
							{
								name:this.project.name,
								path:this.lastfileopened,
								version:this.project.version
							}
						);
					}
				}
			);
			
			switch(this.project.config.files[this.lastfileopened].file_type)
			{
				case 0: // NORMAL
					break;
				case 1: // ARCHIVE
					util.add_interaction(fragment, '<img src="assets/images/archive.png"> Access Files contained inside', () => {
						this.routes.browse(this.project.name, this.lastfileopened + "/");
					});
					util.add_label(
						fragment,
						"This file has been divided into multiple files.",
						["left", "smalltext"]
					);
					break;
				case 2: // VIRTUAL
					util.add_interaction(fragment, '<img src="assets/images/archive.png"> Open Parent File', () => {
						this.routes.file(this.project.name, this.project.config.files[this.lastfileopened].parent);
					});
					util.add_label(
						fragment,
						"This file is part of a bigger file.",
						["left", "smalltext"]
					);
					break;
				case 3: // VIRTUAL_UNDEFINED
					util.add_label(
						fragment,
						"If you see this message, something went wrong.",
						["left", "smalltext"]
					);
					break;
				default:
					break;
			}
			// list strings
			this.strtablecache = [];
			for(let i = 0; i < this.project.string_groups.length; ++i)
			{
				this.prepareGroupOn(fragment, i);
			}
			// add 5 spaces for the bottom part to not cover the last elements
			for(let i = 0; i < 5; ++i)
			{
				util.add_spacer(fragment);
			}
			this.update_main(fragment).then(() => {
				// update the string list with the data
				let scrollTo = this.update_string_list(data);
				// scroll to string (if set)
				if(scrollTo)
				{
					scrollTo.scrollIntoView();
					scrollTo.focus();
					this.nav.update_focus(scrollTo);
				}
				else
					topsection.scrollIntoView();
			});
		}
		catch(err)
		{
			console.error("Exception thrown", err.stack);
			util.push_popup("An unexpected error occured.");
			this.edit.close();
			this.routes.project(this.project.name);
		}
	}

	copy_string() // used in index.html
	{
		if(navigator.clipboard != undefined)
		{
			navigator.clipboard.writeText(this.edit.original.textContent);
			util.push_popup('Original String has been copied');
		}
		else util.push_popup('You need to be on a secure origin to use the Copy button');
	}

	// send and confirm a string change, used in index.html
	// trash = whether the trash button got used instead
	cancel_string()
	{
		this.edit.close();
		this.currentstr.classList.toggle("selected-line", false);
		if(this.nav.has_any())
		{
			this.nav.element.focus({preventScroll: true});
		}
	}

	// send and confirm a string change, used in index.html
	// trash = whether the trash button got used instead
	apply_string(trash = false)
	{
		this.edit.close();
		this.loader.text = "Updating...";
		// folder path of file
		const returnpath = this.project.last_data.path.includes('/') ? this.project.last_data.path.split('/').slice(0, this.project.last_data.path.split('/').length-1).join('/')+'/' : "";
		if(trash)
		{
			this.post(
				"/api/update_string",
				(result_data) => this.update_string_list(result_data),
				() => {
					this.edit.close();
					this.routes.browse(this.project.name, returnpath);
				},
				{
					name:this.project.name,
					version:this.project.version,
					path:this.project.last_data.path,
					group:this.currentstr.group,
					index:this.currentstr.string
				}
			);
		}
		else
		{
			
			this.post(
				"/api/update_string",
				(result_data) => this.update_string_list(result_data),
				() => {
					this.edit.close();
					this.routes.browse(this.project.name, returnpath);
				},
				{
					name:this.project.name,
					version:this.project.version,
					path:this.project.last_data.path,
					group:this.currentstr.group,
					index:this.currentstr.string,
					string:this.edit.translation.value
				}
			);
		}
		this.currentstr.classList.toggle("selected-line", false);
		if(this.nav.has_any())
		{
			this.nav.element.focus({preventScroll: true});
		}
	}

	// update the string list
	update_string_list(data)
	{
		let searched = null;
		try
		{
			const Ix = { // enum for clarity
				SPAN:0,
				MARKER:1,
				TL:2,
				ORI:3,
				USERMARKER:4,
			}
			// update list in memory with received data
			this.project.strings = data.strings;
			this.project.string_groups = data.list;
			let lcstringsearch = "";
			// last searched string
			if(this.search.string != null)
			{
				if(!this.search.casesensitive)
				{
					lcstringsearch = this.search.string.toLowerCase();
				}
				else
				{
					lcstringsearch = this.search.string;
				}
			}
			// set completion tracker
			this.progress.reset(["file"]);
			// iterate over ALL strings
			for(let i = 0; i < this.strtablecache.length; ++i)
			{
				const elems = this.strtablecache[i];
				// retrieve string details
				// s is the local string data
				const s = this.project.string_groups[elems[0].group][elems[0].string];
				// g is the global string data
				const g = this.project.strings[s[0]];
				// user color marker
				if(g[3] != elems[4].state)
				{
					// remove previous class
					if(elems[4].state != 0)
					{
						elems[4].classList.remove(this.constant.marker_classes[elems[4].state]);
					}
					if(g[3] != 0)
					{
						elems[4].classList.add(this.constant.marker_classes[g[3]]);
					}
					elems[4].state = g[3];
				}
				let has_translation = false;
				let target_text = "";
				let target_disabled = false;
				let target_linked = false;

				if(s[2]) // local/linked check
				{
					target_linked = true;
					if(s[1] == null)
					{
						target_text = ""; // default empty if null
						target_disabled = true;
					}
					else
					{
						has_translation = true;
						target_text = s[1];
					}
				}
				else // global
				{
					if(g[1] == null)
					{
						target_text = "";
						target_disabled = true;
					}
					else
					{
						has_translation = true;
						target_text = g[1];
					}
				}
				
				// span
				elems[Ix.SPAN].classList.toggle("unlinked", target_linked);
				elems[Ix.SPAN].classList.toggle("disabled", s[3] != 0);
				// modified marker
				elems[Ix.MARKER].classList.toggle("modified", s[4] != 0);
				// translation
				elems[Ix.TL].classList.toggle("disabled", target_disabled);
				if(elems[Ix.TL].raw_string != target_text)
				{
					elems[Ix.TL].textContent = target_text;
					elems[Ix.TL].raw_string = target_text;
				}
				// update progress
				this.progress.compute_file_string(s[3] != 0, has_translation);
				
				// check if string is the target of a string search
				// if so, store in searched
				if(this.search.string != null && searched == null)
				{
					if(!this.search.casesensitive)
					{
						if(this.search.contains)
						{
							if(
								(
									this.search.useorigin
									&& elems[Ix.ORI].raw_string.toLowerCase().includes(lcstringsearch)
								)
								|| elems[Ix.TL].raw_string.toLowerCase().includes(lcstringsearch)
							)
							{
								searched = elems[0];
							}
						}
						else
						{
							if(
								(
									this.search.useorigin
									&& elems[Ix.ORI].raw_string.toLowerCase() == lcstringsearch
								)
								|| elems[Ix.TL].raw_string.toLowerCase() == lcstringsearch
							)
							{
								searched = elems[0];
							}
						}
					}
					else
					{
						if(this.search.contains)
						{
							if(
								(
									this.search.useorigin
									&& elems[Ix.ORI].raw_string.includes(lcstringsearch)
								)
								|| elems[Ix.TL].raw_string.includes(lcstringsearch)
							)
							{
								searched = elems[0];
							}
						}
						else
						{
							if(
								(
									this.search.useorigin
									&& elems[Ix.ORI].raw_string == lcstringsearch
								)
								|| elems[Ix.TL].raw_string == lcstringsearch
							)
							{
								searched = elems[0];
							}
						}
					}
				}
			}
			// update progress infos
			this.progress.update_and_show([{key:"file", label:"File"}]);
			this.loader.state = false;
		}
		catch(err)
		{
			console.error("Exception thrown", err.stack);
			util.push_popup("An unexpected error occured.");
			this.routes.project(this.project.name);
		}
		// return searched, which contains either null OR a string to scroll to
		return searched;
	}

	// used in index.html
	translate_string()
	{
		this.loader.text = "Fetching translation...";
		this.post(
			"/api/translate_string",
			(data) => {
				this.loader.state = false;
				if(data.translation != null)
				{
					this.edit.translation.value = data.translation;
					this.edit.string_length.innerHTML = this.edit.translation.value.length;
				}
			},
			() => {},
			{
				name:this.project.name,
				string:this.edit.original.textContent
			}
		);
	}

	// base for file browsing via /api/local_path
	local_browse(title, explanation, mode)
	{
		try
		{
			// don't update util.update_page_location here
			
			this.filebrowsingmode = mode;
			// top bar
			this.top_bar.update(
				title,
				() => { // back callback
					switch(this.filebrowsingmode)
					{
						case 0: // new project
						{
							this.routes.main();
							break;
						}
						case 1: // update game
						case 2: // import RPGMTL
						case 3: // import RPGMakerTrans
						{
							this.routes.project(this.project.name);
							break;
						}
						default:
						{
							this.routes.main();
							console.error("Unexpected browsing mode");
							break;
						}
					}
				},
				null,
				{
					home:1
				}
			);
		
			// main part
			let fragment = this.new_page();
			util.add_label(
				fragment,
				explanation
			);
			util.add_interaction(fragment, "RPGMTL", () => {
				this.post(
					"/api/local_path",
					(result_data) => this.update_local_browse(result_data),
					null,
					{
						path:this.constant.working_directory_code,
						mode:this.filebrowsingmode
					}
				);
			}).classList.add("text-button");
			util.add_to(
				fragment,
				"div",
				{
					cls:["left"],
					id:"current_path",
					br:true
				}
			);
			util.add_label(
				fragment,
				"Folders",
				["left"]
			);
			util.add_to(
				fragment,
				"div",
				{
					id:"folder_container",
					br:true
				}
			);
			util.add_label(
				fragment,
				"Files",
				["left"]
			);
			util.add_to(
				fragment,
				"div",
				{
					id:"file_container",
					br:true
				}
			);
			this.update_main(fragment).then(() => {
				this.post(
					"/api/local_path",
					(result_data) => this.update_local_browse(result_data),
					null,
					{
						path:"",
						mode:this.filebrowsingmode
					}
				);
			});
		}
		catch(err)
		{
			console.error("Exception thrown", err.stack);
			util.push_popup("An unexpected error occured.");
			this.edit.close();
			this.routes.project(this.project.name);
		}
	}

	update_local_browse(data)
	{
		// navigation bar
		let path_parts = data.path.split("/");
		// windows driver letter fix
		if(path_parts.length == 2 && path_parts[1] == "" && path_parts[0][1] == ':')
		{
			path_parts.pop();
		}
		// windows root fix
		if(path_parts.length == 1 && path_parts[0] == "")
		{
			path_parts.pop();
		}
		let cpath = document.getElementById("current_path");
		cpath.innerHTML = "";
		let total_path = path_parts[0];
		for(let i = 0; i < path_parts.length; ++i)
		{
			if(i > 0)
			{
				total_path += "/" + path_parts[i];
			}
			const callback_path = total_path;
			util.add_to(
				cpath,
				"div",
				{
					cls:["interact", "text-button"],
					navigable:true,
					innerText:path_parts[i],
					onclick:() => {
						this.post(
							"/api/local_path",
							(result_data) => this.update_local_browse(result_data),
							null,
							{
								"path":callback_path,
								"mode":this.filebrowsingmode
							}
						);
					}
				}
			);
		}
		// update folders
		let container = document.getElementById("folder_container");
		container.innerHTML = "";
		let first_element = null;
		for(let i = 0; i < data.folders.length; ++i)
		{
			const t = data.folders[i];
			const el = util.add_interaction(
				container,
				t.split("/")[t.split("/").length-1],
				() => {
					if(t == "..")
					{
						if(data.path.length == 3 && data.path.endsWith(":/"))
						{
							// special windows case
							this.post(
								"/api/local_path",
								(result_data) => this.update_local_browse(result_data),
								null,
								{
									path:"::",
									mode:this.filebrowsingmode
								}
							);
						}
						else
						{
							// parent directory
							this.post(
								"/api/local_path",
								(result_data) => this.update_local_browse(result_data),
								null,
								{
									path:data.path.split('/').slice(0, data.path.split('/').length-1).join('/'),
									mode:this.filebrowsingmode
								}
							);
						}
					}
					else
					{
						this.post(
							"/api/local_path",
							(result_data) => this.update_local_browse(result_data),
							null,
							{
								path:t,
								mode:this.filebrowsingmode
							}
						);
					}
				}
			);
			if(first_element == null)
			{
				first_element = el;
			}
		}
		container = document.getElementById("file_container");
		container.innerHTML = "";
		let files = data.files.slice();
		// hack to add a "Select this folder button" for game selection
		if(this.filebrowsingmode <= 1 && files.length == 0)
		{
			files.push(data.path + "/Select this Folder");
		}
		
		for(let i = 0; i < files.length; ++i)
		{
			const t = files[i];
			util.add_interaction(container, t.split("/")[t.split("/").length-1], () => {
				switch(this.filebrowsingmode)
				{
					case 0:
					{
						this.post(
							"/api/update_location",
							(result_data) => this.project_creation(result_data),
							null,
							{
								path:t
							}
						);
						break;
					}
					case 1:
					{
						this.post(
							"/api/update_location",
							() => this.routes.redirect_to_project(),
							null,
							{
								name:this.project.name,
								path:t
							}
						);
						break;
					}
					case 2:
					{
						this.post(
							"/api/import",
							() => this.routes.redirect_to_project(),
							null,
							{
								name:this.project.name,
								path:t
							}
						);
						break;
					}
					case 3:
					{
						this.post(
							"/api/import_rpgmtrans",
							() => this.routes.redirect_to_project(),
							null,
							{
								name:this.project.name,
								path:t
							}
						);
						break;
					}
					default:
						break;
				}
			});
		}
		if(first_element != null)
		{
			first_element.focus();
		}
		this.nav.reset(false);
		this.loader.state = false;
	}

	// prompt for replacing strings
	replace_page()
	{
		try
		{
			// top bar
			this.top_bar.update(
				"Replace strings",
				() => { // back callback
					this.routes.project(this.project.name);
				},
				"<ul>\
					<li>This a a tool replace all matching content of Translated Strings with your replacement.</li>\
				</ul>"
			);
		
			// main part
			let fragment = this.new_page();
			util.add_project_title(
				fragment,
				this.project.name
			);
			util.add_label(
				fragment,
				"Replace strings by others (Case Sensitive)",
				["left"]
			);
			util.add_label(
				fragment,
				"String to replace",
				["left", "smalltext"]
			);
			const input = util.add_to(
				fragment,
				"textarea",
				{
					cls:["input", "searchinput", "customarea"],
					navigable:true,
					br:true
				}
			);
			input.rows = "1";
			input.addEventListener('input', () => { // auto update rows on input
				input.rows = "" + input.value.split("\n").length;
			});
			const string_case = util.add_button(
				fragment,
				"Set",
				"assets/images/confirm.png",
				() => {
					string_case.classList.toggle("green");
				},
				true
			);
			string_case.classList.toggle("green", true);
			util.add_to(
				fragment,
				"div",
				{
					cls:["settingtext"],
					innerHTML:"Input is Case sensitive?"
				}
			);
			util.add_label(
				fragment,
				"Replacement",
				["left", "smalltext"]
			);
			const output = util.add_to(
				fragment,
				"textarea",
				{
					cls:["input", "searchinput", "customarea"],
					navigable:true,
					br:true
				}
			);
			output.rows = "1";
			output.addEventListener('input', () => { // auto update rows on input
				output.rows = "" + output.value.split("\n").length;
			});
			util.add_label(
				fragment,
				"Only affect files, whose path contains:",
				["left", "smalltext"]
			);
			const file_match = util.add_to(
				fragment,
				"input",
				{
					cls:["input", "searchinput"],
					navigable:true
				}
			);
			file_match.type = "text";
			file_match.placeholder = "Leave empty to ignore";
			util.add_label(
				fragment,
				"Note: If a matching file contains a compatible string shared with another file, it will be modified in that file as well.",
				["left", "smalltext"]
			);
			
			util.add_to(
				fragment,
				"div",
				{
					cls:["interact", "text-button"],
					navigable:true,
					innerHTML:'<img src="assets/images/copy.png"> Replace',
					onclick:(e) => {
						const file_msg = file_match.value.length ? file_match.value : "None";
						if(input.value == "")
						{
							util.push_popup("The input is empty.");
						}
						else if(
							e.ctrlKey
							|| window.confirm(
								"Replace '"
								+ input.value
								+ "'\nby '"
								+ output.value
								+ "'?\nCase senstivity: "
								+ string_case.classList.contains("green")
								+ "\nMatching files: "
								+ file_msg
							)
						)
						{
							this.post(
								"/api/replace_strings",
								null,
								null,
								{
									name:this.project.name,
									src:input.value,
									dst:output.value,
									casing:string_case.classList.contains("green"),
									file_match:file_match.value
								}
							);
						}
					}
				}
			)
			this.update_main(fragment);
		}
		catch(err)
		{
			console.error("Exception thrown", err.stack);
			util.push_popup("An unexpected error occured.");
			this.edit.close();
			this.routes.project(this.project.name);
		}
	}
	
	focus_and_scroll(el)
	{
		el.focus({preventScroll: true});
		const rect = el.getBoundingClientRect();
		// top bar element (use hardcoded height for speed)
		if(rect.top <= 50)
		{
			this.constant.main.scrollBy(
				0,
				rect.top - 50
			);
		}
		// bottom part (if visible)
		else if(this.constant.bottom.style.display == "")
		{
			const box = this.constant.bottom.getBoundingClientRect();
			if(rect.bottom >= box.top - 2)
			{
				this.constant.main.scrollBy(
					0,
					rect.bottom - box.top + 2
				);
			}
		}
		// bottom of viewport
		else if(rect.bottom >= window.innerHeight - 2)
		{
			this.constant.main.scrollBy(
				0,
				rect.bottom - window.innerHeight + 2
			);
		}
	}
}

var rpgmtl = null;