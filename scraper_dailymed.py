import asyncio
from pyppeteer import launch
import os
import re

async def open_and_iterate_links():
    # Create the extracted directory if it doesn't exist
    output_dir = './extracted_dailymed/'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Launch the browser
    browser = await launch(headless=False)
    page = await browser.newPage()
    await page.goto('https://dailymed.nlm.nih.gov/dailymed/browse-drug-classes.cfm')

    # Extract the list items, their text content, and their href attributes
    li_elements = await page.evaluate('''() => {
        const elements = Array.from(document.querySelectorAll('.index-list li a'));
        return elements.map(element => ({
            text: element.textContent.trim(),
            href: element.href
        }));
    }''')

    # Create a directory for each extracted text and visit each link
    for li_element in li_elements:
        li_text = li_element['text']
        li_href = li_element['href']

        if li_text:  # Ensure the text is not empty
            # Clean the text to create a valid directory name
            cleaned_text = re.sub(r'[^\w\s-]', '', li_text)  # Remove special characters
            cleaned_text = re.sub(r'\s+', '_', cleaned_text)  # Replace whitespace with underscores
            dir_name = cleaned_text[:255]  # Trim to a safe length for directory names

            # Create the directory
            dir_path = os.path.join(output_dir, dir_name)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

            # Append parameters to the URL to get more results per page
            li_href += "&pagesize=200&page=1"

            while True:
                # Visit the link
                await page.goto(li_href)

                # Extract drug info link and NDC codes for each result item
                result_items = await page.evaluate('''() => {
                    const results = Array.from(document.querySelectorAll('div.results article'));
                    return results.map(result => {
                        const drugInfoLink = result.querySelector('a.drug-info-link')?.textContent.trim() || '';
                        const ndcCodes = Array.from(result.querySelectorAll('span.ndc-codes')).map(el => el.textContent.trim()).join('_') || '';
                        const drugInfoHref = result.querySelector('a.drug-info-link')?.href || '';
                        return { drugInfoLink, ndcCodes, drugInfoHref };
                    });
                }''')

                # Create a .txt file for each result item and visit the drug info page
                for result in result_items:
                    if result['drugInfoLink']:
                        # Clean the NDC code to ensure it's valid for a filename
                        cleaned_ndc_codes = re.sub(r'\s+', '', result['ndcCodes'])  # Remove all whitespace
                        cleaned_ndc_codes = re.sub(r'[^\w-]', '', cleaned_ndc_codes)  # Remove non-word characters except hyphens
                        cleaned_ndc_codes = cleaned_ndc_codes.replace('--', '-')  # Replace double hyphens with a single hyphen

                        # Clean the drug info link text
                        cleaned_drug_info_link = re.sub(r'\s+', '_', result['drugInfoLink'])  # Replace whitespace with underscores
                        cleaned_drug_info_link = re.sub(r'[^\w-]', '', cleaned_drug_info_link)  # Remove non-word characters except hyphens

                        # Create a unique filename and trim to a safe length
                        filename = f"{cleaned_drug_info_link}_{cleaned_ndc_codes}.txt"[:255]
                        file_path = os.path.join(dir_path, filename)

                        # Visit the drug info page
                        await page.goto(result['drugInfoHref'])

                        # Extract the entire content of the div with class "drug-label-sections"
                        content = await page.evaluate('''() => {
                            const section = document.querySelector('div.drug-label-sections');
                            if (!section) {
                                return '';
                            }
                            // Remove elements with class 'preview-text'
                            const previewElements = section.querySelectorAll('.preview-text');
                            previewElements.forEach(el => el.remove());

                            // Extract text content of remaining elements
                            return Array.from(section.childNodes)
                                .map(node => node.textContent.trim())
                                .filter(text => text !== '')
                                .join('\\n');
                        }''')

                        # Write to the file
                        with open(file_path, 'w') as file:
                            file.write(content)

                # Check if there is a next page link
                next_page = await page.evaluate('''() => {
                    const nextLink = document.querySelector('a.next-link');
                    return nextLink ? nextLink.href : null;
                }''')

                if next_page:
                    li_href = next_page
                else:
                    break

    # Close the browser
    await browser.close()

def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(open_and_iterate_links())

if __name__ == '__main__':
    main()
