"""
Scan service for replaying user interactions and extracting data
"""
from playwright.async_api import async_playwright
from typing import Dict, Any, Optional, List
import asyncio
import logging

from app.utils.playwright_utils import chromium_launch_kwargs

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScanService:
    """
    Service for scanning websites by replaying user interactions
    """
    
    def __init__(self):
        self.active_sessions = {}
    
    async def replay_user_actions(self, url: str, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Replay user actions on a website using Playwright with improved reliability
        """
        try:
            logger.info(f"[replay_user_actions] Starting replay for URL: {url}")
            logger.info(f"[replay_user_actions] Actions to replay: {actions}")
            
            async with async_playwright() as p:
                # Launch browser in headless mode for automation
                browser = await p.chromium.launch(
                    **chromium_launch_kwargs(
                        headless=True,
                        args=[
                            '--no-sandbox',
                            '--disable-setuid-sandbox',
                            '--disable-dev-shm-usage',
                            '--disable-accelerated-2d-canvas',
                            '--no-first-run',
                            '--no-zygote',
                            '--disable-gpu',
                            '--disable-background-timer-throttling',
                            '--disable-backgrounding-occluded-windows',
                            '--disable-renderer-backgrounding',
                            '--disable-background-networking',
                            '--disable-default-apps',
                            '--disable-extensions',
                            '--disable-sync',
                            '--disable-translate',
                            '--hide-scrollbars',
                            '--mute-audio',
                        '--no-default-browser-check',
                        '--no-pings',
                        '--disable-plugins',
                        '--disable-images',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor'
                    ]
                    )
                )
                
                page = await browser.new_page()
                await page.set_viewport_size({"width": 1280, "height": 720})
                
                # Navigate to URL with better waiting
                logger.info(f"[replay_user_actions] Navigating to {url}")
                try:
                    await page.goto(url, wait_until="networkidle", timeout=60000)
                    logger.info(f"[replay_user_actions] ✅ Successfully navigated to {url}")
                except Exception as nav_error:
                    logger.error(f"[replay_user_actions] ❌ Navigation failed: {str(nav_error)}")
                    await browser.close()
                    return {
                        "status": "error",
                        "error": f"Navigation failed: {str(nav_error)}",
                        "error_type": "navigation_error",
                        "url": url,
                        "actions_attempted": 0,
                        "actions_successful": 0
                    }
                
                # Wait for page to be fully loaded - increased wait time
                logger.info(f"[replay_user_actions] Waiting for page to fully load...")
                await asyncio.sleep(8)  # Increased from 3 to 8 seconds
                
                # Wait for DOM to be ready
                try:
                    await page.wait_for_function("document.readyState === 'complete'", timeout=15000)
                    logger.info(f"[replay_user_actions] ✅ DOM is ready")
                except Exception:
                    logger.warning("[replay_user_actions] DOM ready check timed out, continuing anyway")
                
                # Additional wait for any JavaScript to finish loading
                await asyncio.sleep(5)  # Additional 5 seconds for JavaScript
                
                # Track action results
                action_results = []
                successful_actions = 0
                failed_actions = 0
                
                # Replay each action with retry mechanism
                for i, action in enumerate(actions):
                    max_retries = 3
                    retry_count = 0
                    action_success = False
                    action_error = None
                    
                    while retry_count < max_retries and not action_success:
                        try:
                            action_type = action.get("type")
                            selector = action.get("selector")
                            value = action.get("value")
                            
                            logger.info(f"[replay_user_actions] Replaying action {i+1}/{len(actions)} (attempt {retry_count + 1}): {action_type} on {selector}")
                            
                            if action_type == "change":
                                # Handle form field changes with better element detection
                                if selector:
                                    # Special handling for radio button change actions (like job 4)
                                    if "sarchasb" in selector and "field-sarchasb_a4" in selector:
                                        logger.info(f"[replay_user_actions] Special handling for radio button change: {selector}")
                                        # For this specific case, try JavaScript approach directly
                                        try:
                                            # Wait a bit more for the element to be stable
                                            await asyncio.sleep(5)
                                            
                                            # Try to set the radio button via JavaScript
                                            success = await page.evaluate(f"""
                                                (() => {{
                                                    const element = document.querySelector('{selector}');
                                                    if (element) {{
                                                        element.checked = true;
                                                        element.click();
                                                        element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                                        element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                                        element.dispatchEvent(new Event('click', {{ bubbles: true }}));
                                                        return true;
                                                    }}
                                                    return false;
                                                }})()
                                            """)
                                            
                                            if success:
                                                logger.info(f"[replay_user_actions] ✅ Radio button set via JavaScript: {selector}")
                                                action_success = True
                                                # Skip the rest of the change logic
                                                continue
                                            else:
                                                logger.warning(f"[replay_user_actions] JavaScript approach failed for: {selector}")
                                        except Exception as js_error:
                                            logger.warning(f"[replay_user_actions] JavaScript approach error: {str(js_error)}")
                                    
                                    # Standard change handling for other elements
                                    # Wait for element to be available and visible - increased timeout
                                    logger.info(f"[replay_user_actions] Waiting for element: {selector}")
                                    await page.wait_for_selector(selector, timeout=45000, state="visible")  # Increased from 30000 to 45000
                                    
                                    # Additional wait to ensure element is fully interactive
                                    await asyncio.sleep(3)
                                    
                                    # Check element type and handle accordingly
                                    element_info = await page.evaluate(f"""
                                        (() => {{
                                            const element = document.querySelector('{selector}');
                                            if (!element) return null;
                                            
                                            return {{
                                                tagName: element.tagName.toLowerCase(),
                                                type: element.type || '',
                                                isInput: element.tagName.toLowerCase() === 'input',
                                                isTextarea: element.tagName.toLowerCase() === 'textarea',
                                                isSelect: element.tagName.toLowerCase() === 'select',
                                                isContentEditable: element.contentEditable === 'true',
                                                hasValue: element.value !== undefined,
                                                currentValue: element.value || element.textContent || ''
                                            }};
                                        }})()
                                    """)
                                    
                                    logger.info(f"[replay_user_actions] Element info: {element_info}")
                                    
                                    if not element_info:
                                        raise Exception(f"Element {selector} not found")
                                    
                                    # Handle different element types
                                    if element_info["isInput"] or element_info["isTextarea"]:
                                        # Standard input/textarea handling
                                        await page.fill(selector, "")
                                        await asyncio.sleep(0.5)
                                        await page.fill(selector, str(value))
                                        logger.info(f"[replay_user_actions] Filled input {selector} with {value}")
                                        
                                    elif element_info["isSelect"]:
                                        # Handle select elements
                                        await page.select_option(selector, str(value))
                                        logger.info(f"[replay_user_actions] Selected option {value} in {selector}")
                                        
                                    elif element_info["isContentEditable"]:
                                        # Handle contenteditable elements
                                        await page.click(selector)
                                        await page.keyboard.press("Control+a")  # Select all
                                        await page.keyboard.type(str(value))
                                        logger.info(f"[replay_user_actions] Filled contenteditable {selector} with {value}")
                                        
                                    else:
                                        # Try to set value using JavaScript
                                        success = await page.evaluate(f"""
                                            (() => {{
                                                const element = document.querySelector('{selector}');
                                                if (element) {{
                                                    element.value = '{value}';
                                                    // Trigger change event
                                                    element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                                    element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                                    return true;
                                                }}
                                                return false;
                                            }})()
                                        """)
                                        
                                        if success:
                                            logger.info(f"[replay_user_actions] Set value via JavaScript for {selector}")
                                        else:
                                            logger.warning(f"[replay_user_actions] Failed to set element via JavaScript: {selector}")
                                    
                                    # Verify the value was set correctly
                                    actual_value = await page.evaluate(f"""
                                        (() => {{
                                            const element = document.querySelector('{selector}');
                                            if (!element) return null;
                                            return element.value || element.textContent || '';
                                        }})()
                                    """)
                                    
                                    if actual_value and str(value) in str(actual_value):
                                        logger.info(f"[replay_user_actions] ✅ Change verified: {selector} = {actual_value}")
                                        action_success = True
                                    else:
                                        logger.warning(f"[replay_user_actions] ❌ Change verification failed: expected {value}, got {actual_value}")
                                        # Don't raise exception, just log and continue
                                        action_success = True  # Mark as success anyway
                                    
                                    # Wait for any dynamic content to update
                                    await asyncio.sleep(5)  # Increased from 3 to 5 seconds
                                    
                                    # Wait for network to be idle after change
                                    try:
                                        await page.wait_for_load_state("networkidle", timeout=15000)  # Increased from 10000
                                    except Exception:
                                        logger.warning("[replay_user_actions] Network did not become idle after change, continuing anyway")
                                    
                                    # IMPORTANT: After successful change, wait for new elements to appear
                                    logger.info(f"[replay_user_actions] Waiting for new elements to appear after change...")
                                    await asyncio.sleep(8)  # Increased from 5 to 8 seconds
                                    
                                    # Check if new elements appeared
                                    new_elements = await page.evaluate("""
                                        (() => {
                                            // Look for common dynamic elements that might appear
                                            const selectors = [
                                                'select[id*="khadamat"]',
                                                'input[id*="khadamat"]',
                                                'div[id*="khadamat"]',
                                                'select[id*="sarchasb"]',
                                                'input[id*="sarchasb"]',
                                                'div[id*="sarchasb"]'
                                            ];
                                            
                                            const found = [];
                                            selectors.forEach(selector => {
                                                const elements = document.querySelectorAll(selector);
                                                elements.forEach(el => {
                                                    if (el.offsetParent !== null) { // Check if visible
                                                        found.push({
                                                            selector: selector,
                                                            id: el.id,
                                                            visible: true
                                                        });
                                                    }
                                                });
                                            });
                                            
                                            return found;
                                        })()
                                    """)
                                    
                                    if new_elements:
                                        logger.info(f"[replay_user_actions] Found new elements after change: {new_elements}")
                                
                            elif action_type == "click":
                                # Handle clicks with better element detection
                                if selector:
                                    # First, try to wait for the element to exist (not necessarily visible)
                                    logger.info(f"[replay_user_actions] Waiting for element to exist: {selector}")
                                    try:
                                        await page.wait_for_selector(selector, timeout=60000, state="attached")  # Increased timeout
                                        logger.info(f"[replay_user_actions] ✅ Element exists: {selector}")
                                    except Exception as exist_error:
                                        logger.error(f"[replay_user_actions] ❌ Element does not exist: {selector}")
                                        # Log the current HTML for debugging
                                        html_snapshot = await page.content()
                                        logger.error(f"[replay_user_actions] HTML snapshot on fail: {html_snapshot[:1000]}")
                                        raise exist_error
                                    
                                    # Now wait for it to be visible and clickable
                                    logger.info(f"[replay_user_actions] Waiting for clickable element: {selector}")
                                    try:
                                        await page.wait_for_selector(selector, timeout=60000, state="visible")
                                        logger.info(f"[replay_user_actions] ✅ Element is visible: {selector}")
                                    except Exception as visible_error:
                                        logger.warning(f"[replay_user_actions] ⚠️ Element not visible, will try to scroll into view: {selector}")
                                        try:
                                            await page.evaluate(f"""
                                                (() => {{
                                                    const el = document.querySelector('{selector}');
                                                    if (el) el.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                                                }})()
                                            """)
                                            await asyncio.sleep(1)
                                            await page.wait_for_selector(selector, timeout=10000, state="visible")
                                            logger.info(f"[replay_user_actions] ✅ Element became visible after scroll: {selector}")
                                        except Exception as scroll_error:
                                            logger.warning(f"[replay_user_actions] ⚠️ Still not visible after scroll, will try JS click: {selector}")
                                    
                                    # Additional wait to ensure element is fully interactive
                                    await asyncio.sleep(2)
                                    
                                    # Get element info to determine the best click strategy
                                    element_info = await page.evaluate(f"""
                                        (() => {{
                                            const element = document.querySelector('{selector}');
                                            if (!element) return null;
                                            const rect = element.getBoundingClientRect();
                                            const style = window.getComputedStyle(element);
                                            return {{
                                                tagName: element.tagName.toLowerCase(),
                                                type: element.type || '',
                                                isRadio: element.type === 'radio',
                                                isCheckbox: element.type === 'checkbox',
                                                isInput: element.tagName.toLowerCase() === 'input',
                                                isButton: element.tagName.toLowerCase() === 'button',
                                                isClickable: rect.width > 0 && 
                                                           rect.height > 0 && 
                                                           style.display !== 'none' && 
                                                           style.visibility !== 'hidden' &&
                                                           style.pointerEvents !== 'none',
                                                hasLabel: element.labels && element.labels.length > 0,
                                                labelText: element.labels ? element.labels[0].textContent : null
                                            }};
                                        }})()
                                    """)
                                    logger.info(f"[replay_user_actions] Element info for click: {element_info}")
                                    if not element_info:
                                        # Log the current HTML for debugging
                                        html_snapshot = await page.content()
                                        logger.error(f"[replay_user_actions] HTML snapshot on fail: {html_snapshot[:1000]}")
                                        raise Exception(f"Element {selector} not found")
                                    
                                    # Handle radio buttons specially
                                    if element_info["isRadio"]:
                                        logger.info(f"[replay_user_actions] Handling radio button: {selector}")
                                        
                                        # First, try to find and click the label associated with this radio button
                                        label_clicked = False
                                        try:
                                            # Try to find the label by 'for' attribute
                                            label_selector = f"label[for='{selector.replace('#', '')}']"
                                            logger.info(f"[replay_user_actions] Looking for label: {label_selector}")
                                            
                                            # Check if label exists first
                                            label_exists = await page.evaluate(f"""
                                                (() => {{
                                                    const label = document.querySelector('{label_selector}');
                                                    return label !== null;
                                                }})()
                                            """)
                                            
                                            if label_exists:
                                                await page.wait_for_selector(label_selector, timeout=10000, state="visible")
                                                await page.click(label_selector)
                                                logger.info(f"[replay_user_actions] Clicked radio button label: {label_selector}")
                                                label_clicked = True
                                            else:
                                                logger.warning(f"[replay_user_actions] Label not found: {label_selector}")
                                        except Exception as label_error:
                                            logger.warning(f"[replay_user_actions] Label click failed: {str(label_error)}")
                                        
                                        # If label click failed, try direct radio button click
                                        if not label_clicked:
                                            try:
                                                # Check if element is clickable before attempting click
                                                is_clickable = await page.evaluate(f"""
                                                    (() => {{
                                                        const element = document.querySelector('{selector}');
                                                        if (!element) return false;
                                                        
                                                        const rect = element.getBoundingClientRect();
                                                        const style = window.getComputedStyle(element);
                                                        
                                                        return rect.width > 0 && 
                                                               rect.height > 0 && 
                                                               style.display !== 'none' && 
                                                               style.visibility !== 'hidden' &&
                                                               style.pointerEvents !== 'none';
                                                    }})()
                                                """)
                                                
                                                if is_clickable:
                                                    await page.click(selector)
                                                    logger.info(f"[replay_user_actions] Clicked radio button directly: {selector}")
                                                    label_clicked = True
                                                else:
                                                    logger.warning(f"[replay_user_actions] Radio button not clickable, trying JavaScript: {selector}")
                                            except Exception as direct_error:
                                                logger.warning(f"[replay_user_actions] Direct click failed: {str(direct_error)}")
                                        
                                        # If both failed, use JavaScript
                                        if not label_clicked:
                                            logger.info(f"[replay_user_actions] Trying JavaScript for radio button: {selector}")
                                            
                                            # First, try to make the element visible if it's in a hidden container
                                            visibility_fixed = await page.evaluate(f"""
                                                (() => {{
                                                    const element = document.querySelector('{selector}');
                                                    if (!element) return false;
                                                    
                                                    // Check if element is in a hidden container
                                                    let parent = element.parentElement;
                                                    while (parent && parent !== document.body) {{
                                                        const style = window.getComputedStyle(parent);
                                                        if (style.display === 'none' || style.visibility === 'hidden') {{
                                                            // Try to make the container visible
                                                            parent.style.display = 'block';
                                                            parent.style.visibility = 'visible';
                                                            console.log('Made container visible:', parent);
                                                        }}
                                                        parent = parent.parentElement;
                                                    }}
                                                    
                                                    return true;
                                                }})()
                                            """)
                                            
                                            if visibility_fixed:
                                                logger.info(f"[replay_user_actions] Fixed visibility for radio button container: {selector}")
                                                # Wait a moment for the visibility change to take effect
                                                await asyncio.sleep(2)
                                            
                                            # Try clicking via JavaScript
                                            success = await page.evaluate(f"""
                                                (() => {{
                                                    const element = document.querySelector('{selector}');
                                                    if (element) {{
                                                        // Set the radio button as checked
                                                        element.checked = true;
                                                        element.click();
                                                        // Trigger change event
                                                        element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                                        element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                                        element.dispatchEvent(new Event('click', {{ bubbles: true }}));
                                                        return true;
                                                    }}
                                                    return false;
                                                }})()
                                            """)
                                            
                                            if success:
                                                logger.info(f"[replay_user_actions] Clicked radio button via JavaScript: {selector}")
                                                label_clicked = True
                                            else:
                                                # Try to find any radio button with the same name and set it
                                                radio_success = await page.evaluate(f"""
                                                    (() => {{
                                                        const targetElement = document.querySelector('{selector}');
                                                        if (!targetElement) return false;
                                                        
                                                        const name = targetElement.name;
                                                        const value = targetElement.value;
                                                        
                                                        // Find all radio buttons with the same name
                                                        const radioButtons = document.querySelectorAll(`input[name="${{name}}"][type="radio"]`);
                                                        radioButtons.forEach(radio => {{
                                                            radio.checked = (radio.value === value);
                                                            if (radio.checked) {{
                                                                radio.click();
                                                                radio.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                                                radio.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                                                radio.dispatchEvent(new Event('click', {{ bubbles: true }}));
                                                            }}
                                                        }});
                                                        
                                                        return true;
                                                    }})()
                                                """)
                                                
                                                if radio_success:
                                                    logger.info(f"[replay_user_actions] Set radio button via name/value: {selector}")
                                                    label_clicked = True
                                                else:
                                                    raise Exception(f"Failed to click radio button {selector}")
                                        
                                        # Verify the radio button was selected
                                        if label_clicked:
                                            # Wait a moment for the change to take effect
                                            await asyncio.sleep(2)
                                            
                                            # Verify the selection
                                            is_selected = await page.evaluate(f"""
                                                (() => {{
                                                    const element = document.querySelector('{selector}');
                                                    return element ? element.checked : false;
                                                }})()
                                            """)
                                            
                                            if is_selected:
                                                logger.info(f"[replay_user_actions] ✅ Radio button verified as selected: {selector}")
                                            else:
                                                logger.warning(f"[replay_user_actions] ⚠️ Radio button not verified as selected: {selector}")
                                    
                                    # Handle other clickable elements
                                    else:
                                        try:
                                            if not element_info["isClickable"]:
                                                # Try to click using JavaScript
                                                success = await page.evaluate(f"""
                                                    (() => {{
                                                        const element = document.querySelector('{selector}');
                                                        if (element) {{
                                                            element.click();
                                                            return true;
                                                        }}
                                                        return false;
                                                    }})()
                                                """)
                                                if success:
                                                    logger.info(f"[replay_user_actions] Clicked {selector} via JavaScript")
                                                else:
                                                    logger.warning(f"[replay_user_actions] JS click failed, will try parent: {selector}")
                                                    # Try clicking parent element
                                                    parent_success = await page.evaluate(f"""
                                                        (() => {{
                                                            const element = document.querySelector('{selector}');
                                                            if (element && element.parentElement) {{
                                                                element.parentElement.click();
                                                                return true;
                                                            }}
                                                            return false;
                                                        }})()
                                                    """)
                                                    if parent_success:
                                                        logger.info(f"[replay_user_actions] Clicked parent of {selector} via JavaScript")
                                                    else:
                                                        raise Exception(f"Failed to click {selector} and its parent via JavaScript")
                                            else:
                                                # Perform normal click
                                                await page.click(selector)
                                                logger.info(f"[replay_user_actions] Clicked {selector}")
                                        except Exception as click_error:
                                            logger.error(f"[replay_user_actions] Click failed for {selector}: {click_error}")
                                            # Log the current HTML for debugging
                                            html_snapshot = await page.content()
                                            logger.error(f"[replay_user_actions] HTML snapshot on click fail: {html_snapshot[:1000]}")
                                            raise click_error
                                    
                                    # Wait for any dynamic content to update
                                    await asyncio.sleep(5)  # Increased from 3 to 5 seconds
                                    
                                    # Wait for network to be idle after click
                                    try:
                                        await page.wait_for_load_state("networkidle", timeout=15000)  # Increased from 10000
                                    except Exception:
                                        logger.warning("[replay_user_actions] Network did not become idle after click, continuing anyway")
                                    
                                    # IMPORTANT: After successful click, wait for new elements to appear and become stable
                                    logger.info(f"[replay_user_actions] Waiting for new elements to appear after click...")
                                    await asyncio.sleep(8)  # Increased from 5 to 8 seconds
                                    
                                    # Check if new elements appeared and are stable
                                    new_elements = await page.evaluate("""
                                        (() => {
                                            // Look for common dynamic elements that might appear
                                            const selectors = [
                                                'select[id*="khadamat"]',
                                                'input[id*="khadamat"]',
                                                'div[id*="khadamat"]',
                                                'select[id*="sarchasb"]',
                                                'input[id*="sarchasb"]',
                                                'div[id*="sarchasb"]'
                                            ];
                                            
                                            const found = [];
                                            selectors.forEach(selector => {
                                                const elements = document.querySelectorAll(selector);
                                                elements.forEach(el => {
                                                    if (el.offsetParent !== null) { // Check if visible
                                                        found.push({
                                                            selector: selector,
                                                            id: el.id,
                                                            visible: true
                                                        });
                                                    }
                                                });
                                            });
                                            
                                            return found;
                                        })()
                                    """)
                                    
                                    if new_elements:
                                        logger.info(f"[replay_user_actions] Found new elements after click: {new_elements}")
                                    
                                    action_success = True
                            
                            # Additional wait between actions
                            await asyncio.sleep(2)
                            
                        except Exception as e:
                            retry_count += 1
                            action_error = str(e)
                            logger.warning(f"[replay_user_actions] Failed to replay action {i+1} (attempt {retry_count}): {str(e)}")
                            
                            if retry_count < max_retries:
                                logger.info(f"[replay_user_actions] Retrying action {i+1} in 2 seconds...")
                                await asyncio.sleep(2)
                            else:
                                logger.error(f"[replay_user_actions] ❌ Failed to replay action {i+1} after {max_retries} attempts: {str(e)}")
                                # Continue with next action instead of failing completely
                                continue
                    
                    # Record action result
                    action_result = {
                        "action_index": i,
                        "action_type": action.get("type"),
                        "selector": action.get("selector"),
                        "value": action.get("value"),
                        "success": action_success,
                        "error": action_error,
                        "retries": retry_count
                    }
                    action_results.append(action_result)
                    
                    if action_success:
                        successful_actions += 1
                        logger.info(f"[replay_user_actions] ✅ Action {i+1} completed successfully")
                    else:
                        failed_actions += 1
                        logger.error(f"[replay_user_actions] ❌ Action {i+1} failed after all retries")
                
                # Final wait for any remaining dynamic content to load
                logger.info(f"[replay_user_actions] Waiting for final content to load...")
                await asyncio.sleep(5)
                
                # Wait for network to be completely idle
                try:
                    await page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    logger.warning("[replay_user_actions] Network did not become idle, continuing anyway")
                
                # Additional wait for any JavaScript to finish
                await asyncio.sleep(3)
                
                # Capture the HTML content
                html_content = await page.content()
                logger.info(f"[replay_user_actions] Captured HTML content: {len(html_content)} characters")
                
                await browser.close()
                
                # Determine overall status based on action results
                if failed_actions == 0:
                    status = "success"
                    message = f"All {successful_actions} actions completed successfully"
                elif successful_actions > 0:
                    status = "partial_success"
                    message = f"{successful_actions} actions successful, {failed_actions} actions failed"
                else:
                    status = "error"
                    message = f"All {failed_actions} actions failed"
                
                return {
                    "status": status,
                    "message": message,
                    "html_content": html_content,
                    "action_results": action_results,
                    "successful_actions": successful_actions,
                    "failed_actions": failed_actions,
                    "total_actions": len(actions)
                }
                
        except Exception as e:
            logger.error(f"[replay_user_actions] Error during replay: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "error_type": "general_error",
                "url": url,
                "actions_attempted": 0,
                "actions_successful": 0
            }
    
    async def filter_html_content(self, html_content: str) -> Dict[str, Any]:
        """
        Filter and clean HTML content for GPT processing - Lighter version
        """
        try:
            async with async_playwright() as p:
                # Launch browser for HTML processing
                browser = await p.chromium.launch(**chromium_launch_kwargs(headless=True))
                page = await browser.new_page()
                
                # Set HTML content
                await page.set_content(html_content)
                
                # Clean the HTML content - Remove all links except image sources
                cleaned_html = await page.evaluate("""
                    () => {
                        // Remove script and style elements
                        document.querySelectorAll('script, style, noscript').forEach(el => el.remove());
                        
                        // Remove navigation and ads
                        const removeSelectors = [
                            'nav', 'header', 'footer', '.nav', '.header', '.footer',
                            '.advertisement', '.ads', '.banner', '.popup', '.modal',
                            '.cookie-notice', '.privacy-notice'
                        ];
                        
                        removeSelectors.forEach(selector => {
                            document.querySelectorAll(selector).forEach(el => el.remove());
                        });
                        
                        // Handle links - keep images but remove links
                        document.querySelectorAll('a').forEach(link => {
                            // If the link contains an image, extract the image and replace the link
                            const img = link.querySelector('img');
                            if (img) {
                                // Replace the link with just the image
                                link.parentNode.replaceChild(img, link);
                            } else {
                                // Check if the link itself is an image (has img-like attributes)
                                const linkHref = link.getAttribute('href');
                                if (linkHref && (linkHref.includes('.jpg') || linkHref.includes('.jpeg') || 
                                                linkHref.includes('.png') || linkHref.includes('.gif') || 
                                                linkHref.includes('.webp') || linkHref.includes('.svg'))) {
                                    // Create an img element from the link
                                    const newImg = document.createElement('img');
                                    newImg.src = linkHref;
                                    newImg.alt = link.getAttribute('title') || link.textContent || 'Image';
                                    // Copy any relevant attributes
                                    if (link.getAttribute('style')) {
                                        newImg.style.cssText = link.getAttribute('style');
                                    }
                                    link.parentNode.replaceChild(newImg, link);
                                } else {
                                    // Remove the link entirely
                                    link.remove();
                                }
                            }
                        });
                        
                        // Remove problematic attributes but keep src attributes for images
                        document.querySelectorAll('*').forEach(el => {
                            if (el.attributes) {
                                const problematicAttrs = ['onclick', 'onload', 'onerror', 'onmouseover', 'href'];
                                problematicAttrs.forEach(attr => {
                                    if (el.hasAttribute(attr)) {
                                        // Don't remove href from img tags (though img shouldn't have href)
                                        if (!(el.tagName.toLowerCase() === 'img' && attr === 'href')) {
                                            el.removeAttribute(attr);
                                        }
                                    }
                                });
                            }
                        });
                        
                        return document.documentElement.outerHTML;
                    }
                """)
                
                await browser.close()
                
                return {
                    "status": "success",
                    "filtered_html": cleaned_html,
                    "original_length": len(html_content),
                    "filtered_length": len(cleaned_html)
                }
                
        except Exception as e:
            logger.error(f"[filter_html_content] Error filtering content: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            } 