int max_sum_subarray(int arr[], int n, int k) {
    int window_sum;
    int max_sum;
    int i;

    if (n < k) {
        return -1;
    }

    window_sum = 0;
    i = 0;
    while (i < k) {
        window_sum = window_sum + arr[i];
        i++;
    }

    max_sum = window_sum;

    for (i = k; i < n; i++) {
        window_sum = window_sum + arr[i] - arr[i - k];
        if (window_sum > max_sum) {
            max_sum = window_sum;
        }
    }

    return max_sum;
}

int main() {
    int tc1[6];
    int tc2[5];
    int tc3[9];
    int tc4[4];
    int tc5[1];
    int result;

    tc1[0] = 2;
    tc1[1] = 1;
    tc1[2] = 5;
    tc1[3] = 1;
    tc1[4] = 3;
    tc1[5] = 2;

    tc2[0] = 2;
    tc2[1] = 3;
    tc2[2] = 4;
    tc2[3] = 1;
    tc2[4] = 5;

    tc3[0] = 1;
    tc3[1] = 4;
    tc3[2] = 2;
    tc3[3] = 10;
    tc3[4] = 23;
    tc3[5] = 3;
    tc3[6] = 1;
    tc3[7] = 0;
    tc3[8] = 20;

    tc4[0] = -1;
    tc4[1] = -2;
    tc4[2] = -3;
    tc4[3] = -4;

    tc5[0] = 5;

    printf("=== Max Sum Subarray of Size K ===\n");

    result = max_sum_subarray(tc1, 6, 3);
    printf("TC1: arr=[2,1,5,1,3,2] k=3  -> %d  (expected 9)\n", result);

    result = max_sum_subarray(tc2, 5, 2);
    printf("TC2: arr=[2,3,4,1,5]   k=2  -> %d  (expected 7)\n", result);

    result = max_sum_subarray(tc3, 9, 4);
    printf("TC3: arr=[1,4,2,10,23,3,1,0,20] k=4 -> %d  (expected 39)\n", result);

    result = max_sum_subarray(tc4, 4, 2);
    printf("TC4: arr=[-1,-2,-3,-4] k=2  -> %d  (expected -3)\n", result);

    result = max_sum_subarray(tc5, 1, 1);
    printf("TC5: arr=[5]           k=1  -> %d  (expected 5)\n", result);

    result = max_sum_subarray(tc1, 6, 10);
    printf("TC6: n<k edge case          -> %d  (expected -1)\n", result);

    return 0;
}