import streamlit as st
from llama_index.llms.groq import Groq
import base64
import markdown2
import re

class PresentationGenerator:
    def __init__(self, llm, topic, slide_count):
        self.llm = llm
        self.topic = topic
        self.slide_count = slide_count
        self.outline = None
        self.slides = None

    def generate_outline(self):
        """Generate a comprehensive outline for the topic"""
        outline_prompt = f"""Create a structured outline for '{self.topic}' 
        that can be divided into {self.slide_count} distinct sections. 
        Provide a hierarchical breakdown suitable for a presentation, 
        focusing on key aspects, chronological developments, 
        and significant points."""
        
        response = self.llm.complete(outline_prompt)
        self.outline = str(response).strip()
        return self.outline

    def divide_outline_into_slides(self):
        """Divide the outline into sections for specified number of slides"""
        divide_prompt = f"""Divide the following outline for '{self.topic}' 
        into exactly {self.slide_count} logical sections. 
        Each section should represent a distinct slide topic 
        that flows logically from the previous one.

        Outline:
        {self.outline}

        Provide the divided sections as a numbered list, 
        ensuring comprehensive coverage of the topic."""
        
        response = self.llm.complete(divide_prompt)
        self.slides = str(response).strip().split('\n')
        return self.slides

    def generate_slide_content(self):
        """Generate MARP-formatted slide content"""
        final_slides = []
        
        for i, slide_topic in enumerate(self.slides, 1):
            content_prompt = f"""Create MARP-formatted Markdown content for a slide about:
            '{slide_topic}'

            Formatting Requirements:
            - Use a single header (#) for the slide title
            - Use '-' for bullet points
            - Maximum 3-4 concise bullet points
            - Do no exceed more than5 words in titles
            - extremely concise context for each bullet point
            - Avoid full paragraphs
            - Include key insights and critical information"""
            
            response = self.llm.complete(content_prompt)
            slide_content = str(response).strip()
            
            formatted_slide = (
                f"---\n\n"
                f"# {slide_topic}\n\n"
                f"{slide_content}\n\n"
            )
            final_slides.append(formatted_slide)
        
        return final_slides

    def generate_presentation(self):
        """Orchestrate the entire presentation generation process"""
        marp_header = (
            "---\n"
            "marp: true\n"
            "theme: default\n"
            "size: 16:9\n"
            "paginate: true\n"
            "---\n\n"
        )
        
        title_slide = (
            "---\n\n"
            f"# {self.topic}\n\n"
            "## Comprehensive Overview\n\n"
        )
        
        self.generate_outline()
        self.divide_outline_into_slides()
        slides = self.generate_slide_content()
        
        full_presentation = (
            marp_header + 
            title_slide + 
            ''.join(slides)
        )
        
        return full_presentation

def get_download_link(content, filename, format):
    """Generate download link for file"""
    b64 = base64.b64encode(content.encode()).decode()
    return f'<a href="data:file/{format};base64,{b64}" download="{filename}">Download {format.upper()} File</a>'

def convert_marp_to_html(markdown_content):
    """Convert Marp Markdown to basic HTML"""
    # Basic conversion, can be enhanced
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{markdown_content.split('\n')[2].strip('# ')}</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; }}
            .slide {{ 
                border-bottom: 2px solid #ccc; 
                padding: 20px; 
                margin-bottom: 20px; 
            }}
            h1 {{ color: #333; }}
            ul {{ line-height: 1.6; }}
        </style>
    </head>
    <body>
    """
    
    # Split slides and convert to HTML
    slides = markdown_content.split('---')
    for slide in slides[2:]:  # Skip MARP header and first empty slide
        if slide.strip():
            # Convert Markdown headers and bullet points to HTML
            slide_html = slide.replace('#', '<h1>').replace('\n#', '</h1>\n#')
            slide_html = slide_html.replace('- ', '<li>')
            slide_html = f'<div class="slide">{slide_html}</div>'
            html_content += slide_html
    
    html_content += """
    </body>
    </html>
    """
    
    return html_content

def render_marp_markdown(markdown_content):
    """
    Custom Marp-like rendering for Streamlit
    Converts Marp markdown to a more presentable HTML format with multiple slides
    """
    # Custom styling to mimic Marp presentation
    default_style = """
    <style>
    .marp-container {
        width: 100%;
        max-width: 100%;
        margin: 20px auto;
        position: relative;
    }
    .marp-slides {
        display: flex;
        flex-wrap: nowrap;
        overflow-x: auto;
        scroll-snap-type: x mandatory;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: none;
        -ms-overflow-style: none;
    }
    .marp-slides::-webkit-scrollbar {
        display: none;
    }
    .marp-slide {
        flex: 0 0 100%;
        width: 100%;
        height: 100%;
        scroll-snap-align: start;
        padding: 40px;
        box-sizing: border-box;
        background: white;
        border: 1px solid #ccc;
        margin-right: 20px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        position: relative;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .marp-slide h1 {
        color: #333;
        font-size: 48px;
        margin-bottom: 20px;
        border-bottom: 2px solid #666;
        padding-bottom: 10px;
    }
    .marp-slide ul {
        list-style-type: disc;
        padding-left: 30px;
    }
    .marp-slide li {
        margin-bottom: 15px;
        font-size: 24px;
    }
    .slide-counter {
        position: absolute;
        bottom: 10px;
        right: 20px;
        font-size: 16px;
        color: #888;
    }
    .slide-navigation {
        display: flex;
        justify-content: center;
        margin-top: 20px;
    }
    .slide-navigation button {
        margin: 0 10px;
        padding: 10px 20px;
        background-color: #f0f0f0;
        border: none;
        cursor: pointer;
    }
    </style>
    <script>
    function scrollSlides(direction) {
        const container = document.querySelector('.marp-slides');
        const slideWidth = container.querySelector('.marp-slide').offsetWidth;
        container.scrollBy({
            top: 0,
            left: direction * slideWidth,
            behavior: 'smooth'
        });
    }
    </script>
    """
    
    # Split slides
    slides = markdown_content.split('---')[2:]  # Skip MARP header
    
    # Render slides
    rendered_slides = []
    for i, slide in enumerate(slides, 1):
        if slide.strip():
            # Convert markdown to HTML
            html_content = markdown2.markdown(slide.strip())
            
            # Wrap in slide div with counter
            slide_html = f"""
            <div class="marp-slide">
                {html_content}
                <div class="slide-counter">{i} / {len(slides)}</div>
            </div>
            """
            rendered_slides.append(slide_html)
    
    # Combine everything
    full_html = f"""
    {default_style}
    <div class="marp-container">
        <div class="marp-slides">
            {"".join(rendered_slides)}
        </div>
        <div class="slide-navigation">
            <button onclick="scrollSlides(-1)">Previous</button>
            <button onclick="scrollSlides(1)">Next</button>
        </div>
    </div>
    """
    
    return full_html

def main():
    st.title("Presentation Generator")
    
    # Sidebar for inputs
    st.sidebar.header("Presentation Settings")
    topic = st.sidebar.text_input("Presentation Topic", "Basics of Quantum Computing")
    slide_count = st.sidebar.number_input("Number of Slides", min_value=5, max_value=30, value=20)
    filename = st.sidebar.text_input("Output Filename (without extension)", "my_presentation")
    
    # Generate button
    if st.sidebar.button("Generate Presentation"):
        # Initialize LLM
        llm = Groq(model='llama-3.3-70b-versatile', api_key=st.secrets["GROQ_API_KEY"])
        
        # Generate presentation
        with st.spinner("Generating presentation..."):
            generator = PresentationGenerator(
                llm=llm, 
                topic=topic, 
                slide_count=slide_count
            )
            presentation = generator.generate_presentation()
        
        # Display presentation markdown
        st.markdown("### Generated Presentation Markdown")
        st.code(presentation)
        
        # Render and display presentation
        st.markdown("### Presentation Preview")
        rendered_html = render_marp_markdown(presentation)
        st.components.v1.html(rendered_html, height=700, scrolling=True)
        
        # Prepare download options
        st.markdown("### Download Options")
        
        # Markdown Download
        md_filename = f"{filename}.md"
        md_download_link = f'<a href="data:text/markdown;base64,{base64.b64encode(presentation.encode()).decode()}" download="{md_filename}">Download Markdown</a>'
        st.markdown(md_download_link, unsafe_allow_html=True)
        
        # HTML Download
        html_content = render_marp_markdown(presentation)
        html_filename = f"{filename}.html"
        html_download_link = f'<a href="data:text/html;base64,{base64.b64encode(html_content.encode()).decode()}" download="{html_filename}">Download HTML</a>'
        st.markdown(html_download_link, unsafe_allow_html=True)

if __name__ == "__main__":
    main()