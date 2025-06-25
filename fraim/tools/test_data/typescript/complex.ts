interface User {
  id: number;
  name: string;
  email: string;
}

interface Post {
  id: number;
  title: string;
  content: string;
  authorId: number;
}

/**
 * Fetches a user by their ID
 * @param id The user's ID
 * @returns Promise resolving to the user or null if not found
 */
async function fetchUserById(id: number): Promise<User | null> {
  // Simulate API call
  return {
    id,
    name: "John Doe",
    email: "john@example.com",
  };
}

/**
 * Processes multiple users concurrently
 * @param userIds Array of user IDs to process
 * @returns Promise resolving to array of users
 */
async function processMultipleUsers(
  userIds: number[]
): Promise<(User | null)[]> {
  const promises = userIds.map((id) => fetchUserById(id));
  return Promise.all(promises);
}

class UserService {
  private users: User[] = [];

  /**
   * Creates a new user
   * @param userData The user data to create
   * @returns The created user
   */
  createUser(userData: Omit<User, "id">): User {
    const newUser: User = {
      id: this.users.length + 1,
      ...userData,
    };
    this.users.push(newUser);
    return newUser;
  }

  /**
   * Finds a user by their email
   * @param email The email to search for
   * @returns The user if found, null otherwise
   */
  findUserByEmail(email: string): User | null {
    return this.users.find((user) => user.email === email) || null;
  }
}

// Type guard function
function isUser(obj: any): obj is User {
  return (
    obj &&
    typeof obj.id === "number" &&
    typeof obj.name === "string" &&
    typeof obj.email === "string"
  );
}

// Higher order function
function withErrorHandling<T>(fn: (...args: any[]) => Promise<T>) {
  return async (...args: any[]): Promise<T> => {
    try {
      return await fn(...args);
    } catch (error) {
      console.error("Error:", error);
      throw error;
    }
  };
}

// Decorated function
const safeFetchUser = withErrorHandling(fetchUserById);
