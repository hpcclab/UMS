#include <stdlib.h>
#include <unistd.h>
#include <stdio.h>
#include <stdbool.h>
#include <errno.h>
#include <sys/time.h>
#include <sys/resource.h>
#include <string.h>


long
get_microtime()
{
	struct timeval currentTime;
	gettimeofday(&currentTime, NULL);
	return currentTime.tv_sec * (int)1e6 + currentTime.tv_usec;
}

int
loop()
{
    int counter = 0;
    long current_time;
    FILE *fp;
    char buff[255];
    while (1)
    {
        fp = fopen("/sys/fs/cgroup/memory/memory.usage_in_bytes", "r");
        fgets(buff, 255, (FILE*)fp);
        buff[strcspn(buff, "\n")] = 0;
        fclose(fp);
        current_time = get_microtime();
        printf("%ld Counter: %d %s\n", current_time, counter, buff);
        counter++;
//        2000000000 is approximately 1 second in testbed
        for (unsigned i = 0; i < 200000000; i++) {
            __asm__ __volatile__ ("" : "+g" (i) : :);
        }
    }
    return 0;
}

int
main()
{
    setbuf(stdout, NULL);
    return loop();
}