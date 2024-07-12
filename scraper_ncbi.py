import asyncio
from pyppeteer import launch
import os

async def open_and_iterate_links():
    # Create the extracted directory if it doesn't exist
    output_dir = './extracted/'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    browser = await launch(headless=False)
    page = await browser.newPage()
    await page.goto('https://www.ncbi.nlm.nih.gov/books/NBK430685/')
    
    # Wait for the contents section to load
    await page.waitForSelector('ul.simple-list.toc')
    
    # Extract all links under the "Contents" section
    links = await page.evaluate('''() => {
        const anchors = Array.from(document.querySelectorAll('ul.simple-list.toc li a.toc-item'));
        return anchors.map(anchor => anchor.href);
    }''')
    
    # Iterate through each link and visit
    for link in links:
        await page.goto(link)
        await asyncio.sleep(3)  # Wait for 5 seconds on each page to ensure content loads
        
        # Get the title of the page
        title = await page.evaluate('''() => {
            return document.querySelector('h1 span.title').innerText.trim();
        }''')
        
        # Get the contents of the specified divs
        content = await page.evaluate('''() => {
            const divs = Array.from(document.querySelectorAll('div.jig-ncbiinpagenav.body-content.whole_rhythm div[id]'));
            return divs.map(div => {
                const id = `ID: ${div.id}`;
                let result = [id];
                
                div.childNodes.forEach(node => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        if (node.tagName === 'H2') {
                            result.push(`Header: ${node.innerText}`);
                        } else if (node.tagName === 'P') {
                            result.push(node.innerText);
                        } else if (node.tagName === 'UL') {
                            node.querySelectorAll('li').forEach(li => {
                                result.push(`- ${li.innerText}`);
                            });
                        }
                    }
                });
                
                return result.join('\\n');
            }).join('\\n\\n');
        }''')
        
        # Save content to a file named after the title
        file_name = f"{title}.txt"
        file_path = os.path.join(output_dir, file_name)
        
        with open(file_path, 'w') as f:
            f.write(content)
    
    await browser.close()

def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(open_and_iterate_links())

if __name__ == '__main__':
    main()
