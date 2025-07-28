/**
 * Complex JavaScript file for testing advanced TreeSitter patterns.
 * Contains various function types, classes, and modern JS features.
 */

// Regular function
function calculateTotal(items) {
    return items.reduce((sum, item) => sum + item.price, 0);
}

// Arrow function
const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
};

// Async function
async function fetchUserData(userId) {
    // Simulate API call
    return {
        id: userId,
        name: "Jane Smith",
        email: "jane@example.com",
        preferences: {
            theme: "dark",
            notifications: true
        }
    };
}

// Class with methods
class ShoppingCart {
    constructor() {
        this.items = [];
    }

    addItem(item) {
        this.items.push(item);
        return this.items.length;
    }

    removeItem(itemId) {
        this.items = this.items.filter(item => item.id !== itemId);
        return this.items.length;
    }

    getTotal() {
        return calculateTotal(this.items);
    }
}

// Generator function
function* fibonacciSequence(n) {
    let [a, b] = [0, 1];
    for (let i = 0; i < n; i++) {
        yield a;
        [a, b] = [b, a + b];
    }
}

// Function with default parameters
function createUser(name, role = 'user', isActive = true) {
    return {
        name,
        role,
        isActive,
        createdAt: new Date()
    };
}

// Immediately Invoked Function Expression (IIFE)
const counter = (function() {
    let count = 0;
    return {
        increment() {
            return ++count;
        },
        decrement() {
            return --count;
        },
        getCount() {
            return count;
        }
    };
})();

// Export for module usage
module.exports = {
    calculateTotal,
    formatCurrency,
    fetchUserData,
    ShoppingCart,
    fibonacciSequence,
    createUser,
    counter
};
