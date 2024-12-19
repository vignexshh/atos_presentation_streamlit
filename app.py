import streamlit as st
import time
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
    """Custom Marp-like rendering for Streamlit with header image and footer"""
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
    
    #   navigation script
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
    def __init__(self, llm, topic, slide_count, pdf_text=None, batch_size=2):
        self.llm = llm
        self.topic = topic
        self.slide_count = slide_count
        self.pdf_text = pdf_text
        self.slide_outline = None
        self.final_presentation = None
        self.batch_size = batch_size
        self.pdf_summary = None

    def process_pdf_content(self):
        """Process PDF content and generate a summary using LangChain"""
        if not self.pdf_text:
            return None
            
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )
        chunks = text_splitter.create_documents([self.pdf_text])
        
        chat_model = ChatGroq(
            temperature=0.5,
            groq_api_key=st.secrets["GROQ_API_KEY"],
            model_name="llama-3.3-70b-versatile"
        )
        
        chain = load_summarize_chain(
            llm=chat_model,
            chain_type="map_reduce",
            verbose=False
        )
        
        self.pdf_summary = chain.run(chunks)
        return self.pdf_summary

    def generate_slide_outline(self):
        """Generate a structured outline of slide titles"""
        if self.pdf_text and not self.pdf_summary:
            self.process_pdf_content()
        
        outline_prompt = f"""Create exactly {self.slide_count} slide titles for a presentation on '{self.topic}'.
        {f'Using this summary as reference: {self.pdf_summary}' if self.pdf_summary else ''}
        
        Requirements:
        1. First slide must be an introduction
        2. Last slide should be a conclusion or summary
        3. Titles should be concise (4-6 words maximum)
        4. Each title should represent a distinct aspect or concept
        5. Arrange titles in a logical learning sequence
        
        Format:
        Return only the slide titles, one per line, without numbers or additional text."""

        response = self.llm.complete(outline_prompt)
        self.slide_outline = [title.strip() for title in str(response).strip().split('\n') if title.strip()]
        return self.slide_outline

    def generate_slide_content(self, slide_title, slide_number):
        """Generate content for a specific slide"""
        is_first_slide = slide_number == 1
        is_last_slide = slide_number == self.slide_count
        
        # Use summarized PDF content instead of full text
        pdf_context = f"Based on the summary: {self.pdf_summary}\n" if self.pdf_summary else ""

        if is_first_slide:
            content_prompt = f"""{pdf_context}Create brief introductory content for the first slide titled '{slide_title}' about {self.topic}.
            
            Requirements:
            1. Maximum 3 bullet points
            2. Each point should be one line only
            3. Begin each point with '* '
            4. Focus on what will be covered
            5. No introductory phrases or labels
            6. No empty lines between points"""

        elif is_last_slide:
            content_prompt = f"""{pdf_context}Create conclusion content for the final slide titled '{slide_title}' about {self.topic}.
            
            Requirements:
            1. Maximum 3 bullet points
            2. Each point should be one line only
            3. Begin each point with '* '
            4. Summarize key takeaways
            5. No concluding phrases or labels
            6. No empty lines between points"""

        else:
            content_prompt = f"""{pdf_context}Create content for slide titled '{slide_title}' about {self.topic}.
            
            Requirements:
            1. Maximum 3 bullet points
            2. Each point should be one line only
            3. Begin each point with '* '
            4. Focus on key concepts related to {slide_title}
            5. No introductory phrases or labels
            6. No empty lines between points"""

        response = self.llm.complete(content_prompt)
        return str(response).strip()

    def generate_presentation(self, status_callback=None):
        """Generate the complete presentation in batches"""
        # Generate slide outline first if not already generated
        if not self.slide_outline:
            self.generate_slide_outline()
        
        # Prepare MARP header
        marp_header = "---\nmarp: true\ntheme: default\nsize: 16:9\npaginate: true\n---\n\n"
        
        # Generate content for slides in batches
        slides = []
        total_batches = (len(self.slide_outline) + self.batch_size - 1) // self.batch_size
        
        for batch_idx in range(0, len(self.slide_outline), self.batch_size):
            batch_titles = self.slide_outline[batch_idx:batch_idx + self.batch_size]
            
            if status_callback:
                current_batch = (batch_idx // self.batch_size) + 1
                status_callback(f"Generating content for slides {batch_idx + 1}-{min(batch_idx + self.batch_size, len(self.slide_outline))} (Batch {current_batch}/{total_batches})")
            
            for i, title in enumerate(batch_titles, batch_idx + 1):
                content = self.generate_slide_content(title, i)
                slide = f"---\n\n# {title}\n\n{content}\n\n"
                slides.append(slide)
            
            # Add delay between batches to avoid rate limits
            if batch_idx + self.batch_size < len(self.slide_outline):
                time.sleep(2)  # 2 second delay between batches
        
        self.final_presentation = marp_header + ''.join(slides)
        return self.final_presentation

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
        
        with st.status("Working on Presentation") as status:
            st.write("Generating slide outline...")
            generator = PresentationGenerator(
                llm=llm,
                topic=topic,
                slide_count=slide_count,
                pdf_text=pdf_text,
                batch_size=2  # Process 2 slides at a time
            )
            # Show outline first
            outline = generator.generate_slide_outline()
            st.write("Generated outline:")
            for i, title in enumerate(outline, 1):
                st.write(f"{i}. {title}")

            # Create a progress placeholder
            progress_placeholder = st.empty()
            
            # Generate presentation with status updates
            def update_status(message):
                progress_placeholder.write(message)
            
            presentation = generator.generate_presentation(status_callback=update_status)
            
            status.update(label="Presentation complete!", state="complete")
            progress_placeholder.empty() 
            
            st.write("Generating slide content...")
            presentation = generator.generate_presentation()
            
            st.write("Applying formatting...")
            status.update(label="Presentation complete!", state="complete")
        
        # Display and download options
        st.markdown("### Generated Presentation")
        
        # Add expander for markdown content
        with st.expander("View Markdown Content", expanded=False):
            st.code(presentation)
        
        rendered_html = render_marp_markdown(presentation, header_image_data)
        # Replace footer text placeholder
        rendered_html = rendered_html.replace("{footer_text}", footer_text)
        st.components.v1.html(rendered_html, height=800, scrolling=True)
        
        st.markdown("### Download Options")
        md_download_link = get_download_link(presentation, f"{filename}.md", "markdown")
        html_download_link = get_download_link(rendered_html, f"{filename}.html", "html")
        
        st.markdown(md_download_link, unsafe_allow_html=True)
        st.markdown(html_download_link, unsafe_allow_html=True)

if __name__ == "__main__":
    main()