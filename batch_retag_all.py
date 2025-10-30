#!/usr/bin/env python3
"""
Batch Re-tag All BravoImages Script

This script automatically runs multiple batches of re-tagging until all images
have improved tags with subconcept-first priority.
"""

import asyncio
import logging
import time
from datetime import datetime
from retag_bravo_images import BravoImageRetagger

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('batch_retag_all.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def run_batch_retagging(max_batches=25, batch_size=100):
    """Run multiple batches of re-tagging automatically"""
    
    logger.info("🚀 Starting automated batch re-tagging process")
    logger.info(f"📊 Will process up to {max_batches} batches of {batch_size} images each")
    
    retagger = BravoImageRetagger()
    total_processed = 0
    batch_number = 0
    
    try:
        while batch_number < max_batches:
            batch_number += 1
            batch_start_time = time.time()
            
            logger.info(f"\n🔄 Starting batch {batch_number}/{max_batches}")
            
            # Find images needing re-tagging
            images_to_retag = await retagger.find_images_needing_retag()
            
            if not images_to_retag:
                logger.info("🎉 All images have good tags! Re-tagging complete.")
                break
            
            # Limit batch size
            current_batch_size = min(len(images_to_retag), batch_size)
            images_to_process = images_to_retag[:current_batch_size]
            
            logger.info(f"📊 Found {len(images_to_retag)} images needing tags, processing {current_batch_size} in this batch")
            
            # Process the batch
            success_count = 0
            error_count = 0
            
            # Process in smaller sub-batches of 5 for rate limiting
            for i in range(0, len(images_to_process), 5):
                sub_batch = images_to_process[i:i + 5]
                sub_batch_num = (i // 5) + 1
                total_sub_batches = (len(images_to_process) + 4) // 5
                
                logger.info(f"   🔄 Processing sub-batch {sub_batch_num}/{total_sub_batches}")
                
                for image_data in sub_batch:
                    try:
                        success = await retagger.retag_image(image_data)
                        if success:
                            success_count += 1
                        else:
                            error_count += 1
                        
                        # Rate limiting - 3 second delay between images
                        await asyncio.sleep(3)
                        
                    except Exception as e:
                        logger.error(f"❌ Error processing image: {e}")
                        error_count += 1
            
            total_processed += success_count
            batch_duration = time.time() - batch_start_time
            
            logger.info(f"✅ Batch {batch_number} complete!")
            logger.info(f"📊 Batch results: ✅ {success_count} success, ❌ {error_count} errors")
            logger.info(f"⏱️  Batch duration: {batch_duration:.1f} seconds")
            logger.info(f"🏆 Total processed so far: {total_processed} images")
            
            # Break if no more images to process
            if len(images_to_retag) <= batch_size:
                logger.info("🎉 All remaining images processed!")
                break
            
            # Short break between batches
            logger.info("⏸️  Taking 30-second break between batches...")
            await asyncio.sleep(30)
    
    except KeyboardInterrupt:
        logger.info("🛑 Batch processing interrupted by user")
        logger.info(f"📊 Total processed before interruption: {total_processed} images")
        
    except Exception as e:
        logger.error(f"💥 Fatal error in batch processing: {e}")
        logger.info(f"📊 Total processed before error: {total_processed} images")
        raise
    
    finally:
        logger.info("🏁 Batch re-tagging process finished")
        logger.info(f"📊 Final total processed: {total_processed} images")
        
        # Final status check
        try:
            final_images_needing_tags = await retagger.find_images_needing_retag()
            logger.info(f"📊 Images still needing better tags: {len(final_images_needing_tags)}")
        except Exception as e:
            logger.warning(f"Could not get final count: {e}")

async def main():
    """Main entry point"""
    try:
        # Process up to 25 batches of 100 images each (2500 images total)
        await run_batch_retagging(max_batches=25, batch_size=100)
        
    except KeyboardInterrupt:
        logger.info("🛑 Process interrupted by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())