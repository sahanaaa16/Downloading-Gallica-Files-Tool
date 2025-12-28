#!/bin/bash
# Batch downloader - runs the downloader multiple times to avoid browser timeouts

echo "======================================"
echo "Gallica Batch Downloader"
echo "======================================"
echo ""

TOTAL_RUNS=10  # Run 10 times to ensure all 100 docs are downloaded
CURRENT_RUN=1

while [ $CURRENT_RUN -le $TOTAL_RUNS ]; do
    echo "Run $CURRENT_RUN of $TOTAL_RUNS"
    echo "--------------------------------------"
    
    # Count current PDFs
    PDF_COUNT=$(ls gallica_downloads/*.pdf 2>/dev/null | wc -l | tr -d ' ')
    echo "Current PDFs: $PDF_COUNT"
    
    # Run the downloader
    python3 gallica_stealth_downloader.py
    
    # Count PDFs after run
    NEW_PDF_COUNT=$(ls gallica_downloads/*.pdf 2>/dev/null | wc -l | tr -d ' ')
    echo "PDFs after run: $NEW_PDF_COUNT"
    
    # Check if we got all 100
    if [ "$NEW_PDF_COUNT" -ge 100 ]; then
        echo ""
        echo "✓ All 100 PDFs downloaded!"
        break
    fi
    
    # Check if no new PDFs were downloaded
    if [ "$NEW_PDF_COUNT" -eq "$PDF_COUNT" ]; then
        echo "⚠ No new PDFs downloaded. Waiting 30 seconds before retry..."
        sleep 30
    else
        echo "Downloaded $(($NEW_PDF_COUNT - $PDF_COUNT)) new PDFs"
        echo "Waiting 10 seconds before next run..."
        sleep 10
    fi
    
    CURRENT_RUN=$((CURRENT_RUN + 1))
    echo ""
done

echo ""
echo "======================================"
echo "Final count:"
ls gallica_downloads/*.pdf 2>/dev/null | wc -l
echo "======================================"
