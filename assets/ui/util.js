// static utility functions
class util
{
	static stob64(str) {
		const uint8 = new TextEncoder().encode(str);
		let binary = "";
		for (let byte of uint8) {
			binary += String.fromCharCode(byte);
		}
		return btoa(binary);
	}
	
	static b64tos(b64) {
		const binary = atob(b64);
		const uint8 = new Uint8Array(binary.length);
		for (let i = 0; i < binary.length; i++) {
			uint8[i] = binary.charCodeAt(i);
		}
		return new TextDecoder().decode(uint8);
	}
	
	static filesizeToStr(val)
	{
		if(val >= 1048576)
		{
			return Math.round(val / 1048576) + "MB";
		}
		else if(val >= 1024)
		{
			return Math.round(val / 1024) + "KB";
		}
		else
		{
			return val + "B";
		}
	}
	
	static is_element_in_viewport(el)
	{
		const rect = el.getBoundingClientRect();
		return (
			rect.top >= 0 &&
			rect.left >= 0 &&
			rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
			rect.right <= (window.innerWidth || document.documentElement.clientWidth)
		);
	}
	
	// add an element to the parent node
	static add_to(
		node,
		tagName,
		{
			cls = [], id = null,
			title = null, onload = null,
			onclick = null, onerror = null,
			navigable = false, br = false,
			innerHTML = null, innerText = null,
			textContent = null, value = null
		}={}
	)
	{
		let tag = document.createElement(tagName);
		for(let i = 0; i < cls.length; ++i)
		{
			tag.classList.add(cls[i]);
		}
		if(title)
		{
			tag.title = title;
		}
		if(id)
		{
			tag.id = id;
		}
		if(onload)
		{
			tag.onload = onload;
		}
		if(onclick)
		{
			tag.onclick = onclick;
		}
		if(onerror)
		{
			tag.onerror = onerror;
		}
		if(navigable)
		{
			tag.tabIndex = "0";
		}
		if(innerHTML != null)
		{
			tag.innerHTML = innerHTML;
		}
		if(innerText != null)
		{
			tag.innerText = innerText;
		}
		if(textContent != null)
		{
			tag.textContent = textContent;
		}
		if(value != null)
		{
			tag.textContent = textContent;
		}
		if(node)
		{
			node.appendChild(tag);
		}
		if(br)
		{
			node.appendChild(document.createElement("br"));
		}
		return tag;
	}
	
	// add an interaction text button to the parent node
	static add_interaction(node, innerHTML, callback)
	{
		const interaction = util.add_to(
			node,
			"div",
			{
				cls:["interact", "text-wrapper"],
				onclick:callback,
				navigable:true,
				innerHTML:innerHTML,
				br:true
			}
		);
		return interaction;
	}

	// add a grid cell to the HTML
	// intended to be used with a parent node with the grid css class
	static add_grid_cell(node, innerHTML, callback)
	{
		return util.add_to(
			node,
			"div",
			{
				cls:["interact", "text-wrapper", "grid-cell"],
				onclick:callback,
				innerHTML:innerHTML,
				navigable:true
			}
		);
	}
	
	// add simple input select
	static add_select(node, options, extra_classes, default_select=null)
	{
		const sel = util.add_to(
			node,
			"select",
			{
				cls:["input"].concat(extra_classes),
				navigable:true
			}
		);
		for(let i = 0; i < options.length; ++i)
		{
			const opt = util.add_to(
				sel,
				"option"
			);
			opt.value = options[i];
			opt.textContent = options[i];
			if(options[i] == default_select)
			{
				opt.selected = "selected";
			}
		}
		return sel;
	}
	
	// add a simple text
	static add_title(node, text, extra_classes=[])
	{
		return util.add_to(
			node,
			"div",
			{
				cls:["title"].concat(extra_classes),
				innerText:text,
				br:!extra_classes.includes("inline")
			}
		)
	}
	
	// add a simple vertical space
	static add_spacer(node)
	{
		return util.add_to(
			node,
			"div",
			{
				cls:["spacer"],
				br:true
			}
		);
	}

	// add a button with an image
	static add_button(
		node,
		title,
		img,
		callback,
		navigable
	)
	{
		const btn = util.add_to(
			node,
			"div",
			{
				cls:["interact", "button"],
				title:title,
				onclick:callback,
				navigable:navigable
			}
		);
		btn.style.backgroundPosition = "6px 0px";
		btn.style.backgroundRepeat = "no-repeat";
		if(img)
		{
			btn.style.backgroundImage = (
				"url(\""
				+ img
				+ "\")"
			);
		}
		return btn;
	}

	// display a popup with the given string for 4s
	static push_popup(string)
	{
		let div = document.createElement('div');
		div.className = 'popup';
		div.innerText = string;
		document.body.appendChild(div);
		setTimeout(
			() => util.clear_popup(div),
			4000
		);
	}

	// remove a popup
	static clear_popup(popup)
	{
		popup.parentNode.removeChild(popup);
	}
	
	// set data for the browser to memorize the current page
	static update_page_location(page, name, params)
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
					urlparams.set("params", util.stob64(JSON.stringify(params)));
				}
			}
			let newRelativePathQuery = window.location.pathname + '?' + urlparams.toString();
			history.pushState(null, '', newRelativePathQuery);
		}
	}
	
	// check if target is an input
	static is_not_using_input(el)
	{
		return !(
			["TEXTAREA", "INPUT"].includes(el.tagName)
			|| el.classList.contains("input")
		);
	}
	
	// stop event propagation and default behavior
	static stop_event(e)
	{
		e.stopPropagation();
		e.preventDefault();
	}
	
	// check which special keys are pressed
	// order is shift alt ctrl
	static check_sp_key(e, shift, alt, ctrl)
	{
		return (
			e.shiftKey == shift
			&& e.altKey == alt
			&& e.ctrlKey == ctrl
		);
	}
	
	// used for testing
	static test()
	{
		const lines = new Error().stack.split("\n");
		console.log(
			'%cPassed%c: ' + lines[2].trim().slice(3),
			'background: #197311; color: #ffffff',
			''
		);
	}
}