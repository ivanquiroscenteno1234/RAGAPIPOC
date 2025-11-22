"""PPTX to PDF conversion service using PowerPoint COM automation."""
import os
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def convert_pptx_to_pdf(pptx_content: bytes, original_filename: str) -> tuple[bytes, str]:
    """Convert PPTX content to PDF using PowerPoint automation.
    
    Args:
        pptx_content: PPTX file content as bytes
        original_filename: Original filename (e.g., "presentation.pptx")
        
    Returns:
        Tuple of (PDF content as bytes, PDF filename)
        
    Raises:
        Exception: If conversion fails
    """
    try:
        import comtypes.client
    except ImportError:
        logger.error("comtypes not installed. Cannot convert PPTX to PDF.")
        raise Exception("PPTX to PDF conversion not available (comtypes not installed)")
    
    # Create temp files
    temp_dir = tempfile.gettempdir()
    temp_pptx = os.path.join(temp_dir, f"temp_{os.urandom(8).hex()}.pptx")
    temp_pdf = os.path.join(temp_dir, f"temp_{os.urandom(8).hex()}.pdf")
    
    try:
        # Write PPTX to temp file
        with open(temp_pptx, "wb") as f:
            f.write(pptx_content)
        
        logger.info(f"Converting PPTX to PDF: {original_filename}")
        
        # Initialize PowerPoint
        powerpoint = comtypes.client.CreateObject("PowerPoint.Application")
        powerpoint.Visible = 1
        
        # Open presentation
        presentation = powerpoint.Presentations.Open(temp_pptx, WithWindow=False)
        
        # Save as PDF (32 = ppSaveAsPDF)
        presentation.SaveAs(temp_pdf, 32)
        
        # Close presentation
        presentation.Close()
        powerpoint.Quit()
        
        # Read PDF content
        with open(temp_pdf, "rb") as f:
            pdf_content = f.read()
        
        # Generate PDF filename
        pdf_filename = Path(original_filename).stem + ".pdf"
        
        logger.info(f"Successfully converted {original_filename} to PDF ({len(pdf_content)} bytes)")
        
        return pdf_content, pdf_filename
        
    except Exception as e:
        logger.error(f"Failed to convert PPTX to PDF: {e}")
        raise
    finally:
        # Cleanup temp files
        try:
            if os.path.exists(temp_pptx):
                os.remove(temp_pptx)
            if os.path.exists(temp_pdf):
                os.remove(temp_pdf)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp files: {e}")
