# Two Sum Solution

def two_sum(nums, target):
    num_map = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in num_map:
            return [num_map[complement], i]
        num_map[num] = i

# Example usage
if __name__ == '__main__':
    print(two_sum([2, 7, 11, 15], 9))  # Output: [0, 1]