import streamlit as st
from llama_index.llms.groq import Groq
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.summarize import load_summarize_chain
from langchain_groq import ChatGroq
from langchain.schema import Document
import base64
import markdown2
import tempfile
import os


import streamlit as st
from llama_index.llms.groq import Groq
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.summarize import load_summarize_chain
from langchain_groq import ChatGroq
from langchain.schema import Document
import base64
import markdown2
import tempfile
import os

def get_download_link(content, filename, format):
    """Generate download link for file"""
    b64 = base64.b64encode(content.encode()).decode()
    return f'<a href="data:file/{format};base64,{b64}" download="{filename}">Download {format.upper()} File</a>'

def render_marp_markdown(markdown_content, header_image_data=None):
    """
    Custom Marp-like rendering for Streamlit with header image and footer
    """
    # Convert image data to base64 if provided
    header_image_b64 = ""
    if header_image_data is not None:
        header_image_b64 = base64.b64encode(header_image_data).decode()
    
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
        box-sizing: border-box;
        background: white;
        border: 1px solid #ccc;
        margin-right: 20px;
        display: flex;
        flex-direction: column;
        position: relative;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .slide-header {
        width: 100%;
        height: 10%;
        overflow: hidden;
        position: relative;
        background-color: #f5f5f5;
    }
    .slide-header img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    .slide-content {
        padding: 40px;
        flex-grow: 1;
    }
    .slide-footer {
        height: 5px;
        background-color: #4f46e5;
        width: 100%;
        position: relative;
    }
    .footer-text {
        position: absolute;
        bottom: 10px;
        left: 20px;
        color: white;
        font-size: 12px;
        z-index: 2;
    }
    .marp-slide h1 {
        color: #333;
        font-size: 36px;
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
        font-size: 20px;
        line-height: 1.4;
    }
    .slide-counter {
        position: absolute;
        bottom: 10px;
        right: 20px;
        font-size: 14px;
        color: #888;
    }
    .slide-navigation {
        display: flex;
        justify-content: center;
        margin-top: 20px;
        gap: 10px;
    }
    .slide-navigation button {
        padding: 8px 16px;
        background-color: #f0f0f0;
        border: 1px solid #ddd;
        border-radius: 4px;
        cursor: pointer;
        transition: background-color 0.3s;
    }
    .slide-navigation button:hover {
        background-color: #e0e0e0;
    }
    </style>
    """
    
    # Split slides
    slides = markdown_content.split('---')[2:]  # Skip MARP header
    
    # Process each slide
    rendered_slides = []
    for i, slide in enumerate(slides, 1):
        if slide.strip():
            # Convert markdown to HTML
            html_content = markdown2.markdown(slide.strip())
            
            # Create header image HTML based on whether an image was provided
            header_html = """<div class="slide-header">"""
            if header_image_b64:
                header_html += f"""<img src="data:image/png;base64,{header_image_b64}" alt="Header Image">"""
            header_html += "</div>"
            
            # Wrap in slide div with header image and footer
            slide_html = f"""
            <div class="marp-slide">
                {header_html}
                <div class="slide-content">
                    {html_content}
                </div>
                <div class="slide-footer">
                    <div class="footer-text">{{footer_text}}</div>
                </div>
                <div class="slide-counter">{i} / {len(slides)}</div>
            </div>
            """
            rendered_slides.append(slide_html)
    
    # Add navigation script
    navigation_script = """
    <script>
    function scrollSlides(direction) {
        const container = document.querySelector('.marp-slides');
        const slideWidth = container.querySelector('.marp-slide').offsetWidth;
        const currentScroll = container.scrollLeft;
        container.scrollTo({
            left: currentScroll + (direction * slideWidth),
            behavior: 'smooth'
        });
    }
    </script>
    """
    
    # Combine everything
    full_html = f"""
    {default_style}
    {navigation_script}
    <div class="marp-container">
        <div class="marp-slides">
            {"".join(rendered_slides)}
        </div>
        <div class="slide-navigation">
            <button onclick="scrollSlides(-1)">← Previous</button>
            <button onclick="scrollSlides(1)">Next →</button>
        </div>
    </div>
    """
    
    return full_html

class PresentationGenerator:
    def __init__(self, llm, topic, slide_count, pdf_text=None):
        self.llm = llm
        self.topic = topic
        self.slide_count = slide_count
        self.pdf_text = pdf_text
        self.outline = None
        self.slides = None

    def process_pdf_content(self):
        """Generate outline from PDF content using LangChain"""
        if not self.pdf_text:
            return None
            
        # Initialize LangChain components
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )
        
        # Create document chunks
        chunks = text_splitter.create_documents([self.pdf_text])
        
        # Create LangChain chat model
        chat_model = ChatGroq(
            temperature=0.5,
            groq_api_key=st.secrets["GROQ_API_KEY"],
            model_name="llama-3.3-70b-versatile"
        )
        
        # Load summarization chain
        chain = load_summarize_chain(
            llm=chat_model,
            chain_type="map_reduce",
            verbose=False
        )
        
        # Generate summary from PDF content
        summary = chain.run(chunks)
        return summary

    def generate_outline(self):
        """Generate a comprehensive outline for the topic"""
        pdf_summary = self.process_pdf_content() if self.pdf_text else None
        
        outline_prompt = f"""Create a detailed outline for a presentation on '{self.topic}' with {self.slide_count} distinct sections.
        {f'Using this document as reference: {pdf_summary}' if pdf_summary else ''}
        
        Requirements:
        1. Each section should cover a unique aspect of {self.topic}
        2. Sections should flow logically from introduction to conclusion
        3. Focus on key concepts, practical applications, and important insights
        4. Do not include presentation instructions or slide formatting notes
        5. Do not repeat content across sections"""
        
        response = self.llm.complete(outline_prompt)
        self.outline = str(response).strip()
        return self.outline

    def divide_outline_into_slides(self):
        """Divide the outline into sections for specified number of slides"""
        divide_prompt = f"""Transform this outline into {self.slide_count} distinct slides about {self.topic}:

        {self.outline}

        Requirements:
        1. Each slide should focus on a single main concept
        2. Maintain logical flow between slides
        3. Create concise, clear titles
        4. Do not include any formatting instructions
        5. Do not repeat content between slides
        6. Do not number or label slides as 'Slide X'"""
        
        response = self.llm.complete(divide_prompt)
        self.slides = str(response).strip().split('\n')
        return self.slides

    def generate_slide_content(self):
        """Generate MARP-formatted slide content"""
        final_slides = []
        
        for i, slide_topic in enumerate(self.slides, 1):
            content_prompt = f"""Create content for a slide about: {slide_topic}

            Requirements:
            1. Include 2-3 key points with `##` that directly relate to {slide_topic}
            2. Each point should be clear and informative
            3. Avoid repetition from other slides
            4. Do not include formatting instructions or slide numbers
            5. Do not include phrases like 'Key Points:' or 'Features:'
            6. Focus only on meaningful content"""
            
            response = self.llm.complete(content_prompt)
            slide_content = str(response).strip()
            
            # Clean up common formatting issues
            slide_content = (slide_content
                           .replace('Key Points:', '')
                           .replace('Features:', '')
                           .replace('* Title:', '')
                           .replace('* Text:', '')
                           .strip())
            
            formatted_slide = f"---\n\n# {slide_topic}\n\n{slide_content}\n\n"
            final_slides.append(formatted_slide)
        
        return final_slides

    def generate_presentation(self):
        """Generate complete presentation"""
        marp_header = "---\nmarp: true\ntheme: default\nsize: 16:9\npaginate: true\n---\n\n"
        title_slide = f"---\n\n# {self.topic}\n\n"
        
        self.generate_outline()
        self.divide_outline_into_slides()
        slides = self.generate_slide_content()
        
        return marp_header + title_slide + ''.join(slides)

def main():
    st.title("EPG Agent")
    
    # Sidebar inputs
    st.sidebar.header("Presentation Settings")
    topic = st.sidebar.text_input("Presentation Topic", "Brief Introduction to concepts of map reduce")
    slide_count = st.sidebar.number_input("Number of Slides", min_value=5, max_value=10, value=5)
    
    # File uploader for header image
    header_image_file = st.sidebar.file_uploader("Upload Header Image", type=['png', 'jpg', 'jpeg'])
    header_image_data = None
    if header_image_file is not None:
        header_image_data = header_image_file.read()
    
    footer_text = st.sidebar.text_input("Footer Text", "Your Company Name")
    
    # PDF upload option
    pdf_file = st.sidebar.file_uploader("Upload PDF for Content (Optional)", type=['pdf'])
    pdf_text = None
    if pdf_file:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(pdf_file.getvalue())
                tmp_file_path = tmp_file.name
            
            # Load PDF content
            loader = PyPDFLoader(tmp_file_path)
            pages = loader.load_and_split()
            pdf_text = "\n".join([page.page_content for page in pages])
            os.unlink(tmp_file_path)
            
            st.sidebar.success("PDF processed successfully!")
        except Exception as e:
            st.sidebar.error(f"Error processing PDF: {str(e)}")
            pdf_text = None
    
    filename = st.sidebar.text_input("Output Filename", "presentation")
    
    if st.sidebar.button("Generate Presentation"):
        llm = Groq(
            model='llama-3.2-3b-preview',
            api_key=st.secrets["GROQ_API_KEY"]
        )
        
        with st.spinner("Generating presentation..."):
            generator = PresentationGenerator(
                llm=llm,
                topic=topic,
                slide_count=slide_count,
                pdf_text=pdf_text
            )
            presentation = generator.generate_presentation()
        
        # Display and download options
        st.markdown("### Generated Presentation")
        st.code(presentation)
        
        rendered_html = render_marp_markdown(presentation, header_image_data)
        # Replace footer text placeholder
        rendered_html = rendered_html.replace("{footer_text}", footer_text)
        st.components.v1.html(rendered_html, height=700, scrolling=True)
        
        st.markdown("### Download Options")
        md_download_link = get_download_link(presentation, f"{filename}.md", "markdown")
        html_download_link = get_download_link(rendered_html, f"{filename}.html", "html")
        
        st.markdown(md_download_link, unsafe_allow_html=True)
        st.markdown(html_download_link, unsafe_allow_html=True)

if __name__ == "__main__":
    main()