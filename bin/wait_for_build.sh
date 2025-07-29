#!/bin/bash

echo "MT4 Docker Build Monitor"
echo "======================="

# Check if build is running
check_build_status() {
    if ps aux | grep -q "[d]ocker compose build"; then
        return 0  # Build is running
    else
        return 1  # Build is not running
    fi
}

# Check if image exists
check_image() {
    if docker images | grep -q "mt4-docker_mt4"; then
        return 0  # Image exists
    else
        return 1  # Image doesn't exist
    fi
}

# Monitor build
echo "Checking build status..."
start_time=$(date +%s)

while true; do
    current_time=$(date +%s)
    elapsed=$((current_time - start_time))
    minutes=$((elapsed / 60))
    seconds=$((elapsed % 60))
    
    if check_build_status; then
        # Get last few lines of build log
        if [ -f build.log ]; then
            echo -ne "\r[${minutes}m ${seconds}s] Building... "
            tail -1 build.log | grep -oE "#[0-9]+ \[[^]]+\]" | tail -1
        else
            echo -ne "\r[${minutes}m ${seconds}s] Building..."
        fi
    else
        # Build process not running, check if completed
        if check_image; then
            echo -e "\n\n✓ Build completed successfully!"
            echo ""
            echo "Next steps:"
            echo "1. Update .env with your MT4 credentials:"
            echo "   nano .env"
            echo ""
            echo "2. Start the container:"
            echo "   docker compose up -d"
            echo ""
            echo "3. Monitor logs:"
            echo "   ./monitor.sh"
            exit 0
        else
            # Check if build failed
            if [ -f build.log ] && grep -q "ERROR" build.log; then
                echo -e "\n\n✗ Build failed!"
                echo "Check build.log for errors:"
                echo ""
                tail -20 build.log | grep -E "(ERROR|error:|failed)"
                exit 1
            else
                echo -e "\n\n⚠ Build process not running and image not found"
                echo "Starting build..."
                nohup docker compose build > build.log 2>&1 &
                sleep 2
            fi
        fi
    fi
    
    sleep 2
done